import json
import logging
import os
import threading
from datetime import datetime

from backend.database import Analysis, SessionLocal, update_analysis
from backend.models import get_output_dir, get_subtitle_dir

logger = logging.getLogger("ytdupe.worker")


class _CancelledError(Exception):
    pass


_active_jobs: dict[str, threading.Thread] = {}
_cancel_flags: dict[str, threading.Event] = {}


def run_analysis(job_id: str, channel_url: str, threshold: float, use_stemming: bool, exclude_series: bool, metadata_csv: str = "", audio_fallback: bool = True, whisper_model: str = "small", mode: str = "duplicate"):
    cancel_event = threading.Event()
    _cancel_flags[job_id] = cancel_event
    t = threading.Thread(
        target=_worker,
        args=(job_id, channel_url, threshold, use_stemming, exclude_series, metadata_csv, audio_fallback, whisper_model, cancel_event, mode),
        daemon=True,
    )
    _active_jobs[job_id] = t
    t.start()


def cancel_analysis(job_id: str) -> bool:
    flag = _cancel_flags.get(job_id)
    if flag:
        flag.set()
        return True
    return False


def _worker(job_id: str, channel_url: str, threshold: float, use_stemming: bool, exclude_series: bool, metadata_csv: str, audio_fallback: bool = True, whisper_model: str = "small", cancel_event: threading.Event | None = None, mode: str = "duplicate"):
    db = SessionLocal()
    short_id = job_id[:8]

    def _check_cancel():
        if cancel_event and cancel_event.is_set():
            raise _CancelledError()

    try:
        if mode == "thumbnail":
            _run_thumbnail_pipeline(db, job_id, channel_url, threshold, metadata_csv, short_id, _check_cancel)
            return
        logger.info("▶ [%s] START  channel=%s  threshold=%.2f  stemming=%s  exclude_series=%s",
                     short_id, channel_url, threshold, use_stemming, exclude_series)

        from ytdupe.downloader import download_subtitles

        subtitle_dir = get_subtitle_dir(job_id)
        _last_log_pct = [0]

        def on_download_progress(current: int, total: int, video_id: str):
            _check_cancel()
            pct = 5 + round((current / total) * 20)
            _set_progress(db, job_id, pct, f"Download subtitle {current}/{total}")
            if pct - _last_log_pct[0] >= 5 or current == total:
                _last_log_pct[0] = pct
                logger.info("⬇ [%s] %3d%%  download %d/%d  (%s)", short_id, pct, current, total, video_id)

        _set_progress(db, job_id, 5, "Memulai download subtitle...")

        result = download_subtitles(
            channel_url=channel_url,
            lang_priority=["id", "en"],
            output_dir=subtitle_dir,
            sleep_interval=5,
            on_progress=on_download_progress,
        )
        success_count = len(result["success"])
        fail_count = len(result["failed"])

        logger.info("⬇ [%s]  25%%  subtitle done — %d ok, %d fail", short_id, success_count, fail_count)
        _set_progress(db, job_id, 25, f"Subtitle selesai: {success_count} berhasil, {fail_count} gagal")

        failed_ids = [vid_id for vid_id, _reason in result["failed"]]
        audio_count = 0

        if audio_fallback and failed_ids:
            import shutil
            from ytdupe.transcriber import transcribe_videos

            audio_tmp_dir = os.path.join(os.path.dirname(subtitle_dir), "audio_tmp")
            logger.info("🎤 [%s]  26%%  starting audio transcription for %d videos (model=%s)",
                        short_id, len(failed_ids), whisper_model)

            def on_transcribe_progress(current: int, total: int, video_id: str):
                _check_cancel()
                pct = 26 + round((current / total) * 24)
                _set_progress(db, job_id, pct, f"Transkripsi audio {current}/{total} — {video_id}")

            audio_results = transcribe_videos(
                video_ids=failed_ids,
                output_dir=subtitle_dir,
                audio_tmp_dir=audio_tmp_dir,
                model_size=whisper_model,
                language="id",
                on_progress=on_transcribe_progress,
            )
            audio_count = len(audio_results)
            shutil.rmtree(audio_tmp_dir, ignore_errors=True)

            logger.info("🎤 [%s]  50%%  audio transcription done — %d/%d successful",
                        short_id, audio_count, len(failed_ids))
            update_analysis(db, job_id, audio_transcribed_count=audio_count)

        _set_progress(db, job_id, 50, f"Subtitle: {success_count}, Audio: {audio_count}")

        _set_progress(db, job_id, 55, "Parsing transkrip...")
        from ytdupe.parser import parse_all_subtitles

        transcripts = parse_all_subtitles(subtitle_dir)

        if not transcripts:
            _set_status(db, job_id, "failed", "Tidak ada transkrip ditemukan")
            logger.error("✖ [%s]  55%%  0 transcripts parsed", short_id)
            return

        logger.info("✓ [%s]  55%%  parsed %d transcripts", short_id, len(transcripts))

        _set_progress(db, job_id, 60, f"Preprocessing {len(transcripts)} transkrip...")
        normalized = _normalize_or_fail(transcripts, use_stemming)
        if normalized is None:
            _set_status(db, job_id, "failed", "Semua transkrip kosong setelah preprocessing")
            logger.error("✖ [%s]  50%%  all transcripts empty after preprocessing", short_id)
            return

        logger.info("✓ [%s]  55%%  %d transcripts normalized (stemming=%s)", short_id, len(normalized), use_stemming)
        result = _compute_duplicate_result(
            transcripts=transcripts,
            normalized=normalized,
            channel_url=channel_url,
            threshold=threshold,
            use_stemming=use_stemming,
            exclude_series=exclude_series,
            metadata_csv=metadata_csv,
            output_dir=get_output_dir(job_id),
            progress=lambda pct, msg: _set_progress(db, job_id, pct, msg),
            log_prefix=short_id,
            mode=mode,
        )
        clusters = result["clusters"]
        video_ids = result["video_ids"]
        analyzed_transcripts = result["transcripts"]
        total_dupes = sum(c["cluster_size"] - 1 for c in clusters)

        update_analysis(db, job_id,
            status="completed",
            progress=100,
            progress_message="Analisis selesai!",
            total_videos=len(video_ids),
            total_clusters=len(clusters),
            total_duplicates=total_dupes,
            clusters_json=clusters,
            transcripts_json=analyzed_transcripts,
            video_ids_json=video_ids,
            excel_path=result["excel_path"],
            subtitle_dir=subtitle_dir,
            metadata_csv=metadata_csv,
            finished_at=datetime.utcnow(),
        )
        logger.info("✅ [%s] 100%%  DONE — %d videos, %d clusters, %d duplicates",
                     short_id, len(video_ids), len(clusters), total_dupes)

    except _CancelledError:
        logger.info("⏹ [%s] CANCELLED by user", short_id)
        _set_status(db, job_id, "cancelled", "Dibatalkan oleh pengguna")
    except Exception as e:
        logger.exception("✖ [%s] ERROR — %s", short_id, e)
        _set_status(db, job_id, "failed", str(e)[:200])
    finally:
        db.close()
        _active_jobs.pop(job_id, None)
        _cancel_flags.pop(job_id, None)


def _run_thumbnail_pipeline(db, job_id, channel_url, threshold, metadata_csv, short_id, check_cancel):
    from ytdupe.downloader import list_video_ids
    from ytdupe.thumbnail import download_thumbnails, compute_thumbnail_hashes, compute_thumbnail_similarity_matrix
    from ytdupe.similarity import cluster_duplicates
    from ytdupe.utils import load_metadata
    from ytdupe.reporter import generate_report

    _set_progress(db, job_id, 2, "Mengambil daftar video...")
    video_ids = list_video_ids(channel_url)
    logger.info("📋 [%s]   5%%  found %d videos", short_id, len(video_ids))
    _set_progress(db, job_id, 5, f"Ditemukan {len(video_ids)} video")

    if not video_ids:
        _set_status(db, job_id, "failed", "Tidak ada video ditemukan")
        return

    thumb_dir = os.path.join(os.path.dirname(get_subtitle_dir(job_id)), "thumbnails")

    def on_thumb_progress(current, total, video_id):
        check_cancel()
        pct = 5 + round((current / total) * 35)
        _set_progress(db, job_id, pct, f"Download thumbnail {current}/{total}")

    thumb_paths = download_thumbnails(video_ids, thumb_dir, on_progress=on_thumb_progress)
    video_ids = list(thumb_paths.keys())
    logger.info("🖼 [%s]  40%%  downloaded %d thumbnails", short_id, len(thumb_paths))

    if len(video_ids) < 2:
        _set_status(db, job_id, "failed", "Kurang dari 2 thumbnail berhasil didownload")
        return

    _set_progress(db, job_id, 42, "Menghitung hash thumbnail...")
    check_cancel()
    hashes = compute_thumbnail_hashes(thumb_paths)

    _set_progress(db, job_id, 55, "Menghitung kemiripan thumbnail...")
    check_cancel()
    sim_matrix, pairs = compute_thumbnail_similarity_matrix(hashes, video_ids, threshold)
    logger.info("📊 [%s]  60%%  %d pairs above threshold %.2f", short_id, len(pairs), threshold)

    _set_progress(db, job_id, 65, "Mengelompokkan cluster...")
    metadata_df = load_metadata(metadata_csv)
    clusters = cluster_duplicates(pairs, video_ids, metadata=metadata_df)
    total_dupes = sum(c["cluster_size"] - 1 for c in clusters)

    _set_progress(db, job_id, 75, "Membuat laporan Excel...")
    output_dir = get_output_dir(job_id)
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, "laporan_duplikat_konten.xlsx")

    generate_report(
        output_path=excel_path,
        transcripts={},
        clusters=clusters,
        metadata=metadata_df,
        similarity_matrix=sim_matrix,
        video_ids=video_ids,
        config={"channel_url": channel_url, "similarity_threshold": threshold, "mode": "thumbnail"},
    )

    update_analysis(db, job_id,
        status="completed",
        progress=100,
        progress_message="Analisis selesai!",
        total_videos=len(video_ids),
        total_clusters=len(clusters),
        total_duplicates=total_dupes,
        clusters_json=clusters,
        transcripts_json={},
        video_ids_json=video_ids,
        excel_path=excel_path,
        finished_at=datetime.utcnow(),
    )
    logger.info("✅ [%s] 100%%  DONE — %d videos, %d clusters, %d duplicates", short_id, len(video_ids), len(clusters), total_dupes)


def _set_progress(db, job_id: str, progress: int, message: str):
    update_analysis(db, job_id, progress=progress, progress_message=message)


def _set_status(db, job_id: str, status: str, message: str):
    update_analysis(db, job_id, status=status, progress_message=message)
    if status in ("failed", "cancelled"):
        update_analysis(db, job_id, finished_at=datetime.utcnow())


def recompute_completed_analysis(db, analysis_id: str, metadata_csv: str):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        return None

    transcripts = json.loads(analysis.transcripts_json) if analysis.transcripts_json else {}
    if not transcripts and analysis.subtitle_dir:
        from ytdupe.parser import parse_all_subtitles

        transcripts = parse_all_subtitles(analysis.subtitle_dir)

    normalized = _normalize_or_fail(transcripts, bool(analysis.use_stemming))
    if normalized is None:
        raise ValueError("Tidak ada transkrip yang bisa dianalisis ulang")

    result = _compute_duplicate_result(
        transcripts=transcripts,
        normalized=normalized,
        channel_url=analysis.channel_url,
        threshold=analysis.threshold or 0.75,
        use_stemming=bool(analysis.use_stemming),
        exclude_series=bool(analysis.exclude_series),
        metadata_csv=metadata_csv,
        output_dir=get_output_dir(analysis_id),
        mode=analysis.mode or "duplicate",
    )
    clusters = result["clusters"]
    total_dupes = sum(c["cluster_size"] - 1 for c in clusters)

    return update_analysis(
        db,
        analysis_id,
        total_videos=len(result["video_ids"]),
        total_clusters=len(clusters),
        total_duplicates=total_dupes,
        clusters_json=clusters,
        transcripts_json=result["transcripts"],
        video_ids_json=result["video_ids"],
        excel_path=result["excel_path"],
        metadata_csv=metadata_csv,
    )


def _normalize_or_fail(transcripts: dict[str, str], use_stemming: bool):
    from ytdupe.preprocess import normalize_transcripts

    normalized = normalize_transcripts(transcripts, use_stemming=use_stemming)
    return normalized or None


def _compute_duplicate_result(
    transcripts: dict[str, str],
    normalized: dict[str, str],
    channel_url: str,
    threshold: float,
    use_stemming: bool,
    exclude_series: bool,
    metadata_csv: str,
    output_dir: str,
    progress=None,
    log_prefix: str | None = None,
    mode: str = "duplicate",
):
    from ytdupe.reporter import generate_report
    from ytdupe.similarity import (
        build_tfidf_matrix,
        cluster_duplicates,
        compute_similarity_matrix,
        find_duplicates,
    )
    from ytdupe.utils import load_metadata

    def set_progress(pct: int, message: str):
        if progress:
            progress(pct, message)

    set_progress(60, "Membangun TF-IDF matrix...")
    tfidf_matrix, _vectorizer, video_ids = build_tfidf_matrix(normalized)
    if log_prefix:
        logger.info("✓ [%s]  65%%  TF-IDF matrix built (%d videos × %d features)",
                    log_prefix, len(video_ids), tfidf_matrix.shape[1])

    set_progress(70, "Menghitung similarity...")
    sim_matrix = compute_similarity_matrix(tfidf_matrix)
    if log_prefix:
        logger.info("✓ [%s]  75%%  similarity matrix computed", log_prefix)

    metadata_df = load_metadata(metadata_csv)

    set_progress(80, f"Mencari duplikat (threshold={threshold})...")
    pairs = find_duplicates(
        sim_matrix,
        video_ids,
        threshold=threshold,
        exclude_series=exclude_series,
        metadata=metadata_df,
        mode=mode,
    )
    if log_prefix:
        logger.info("✓ [%s]  82%%  %d duplicate pairs found (threshold=%.2f)", log_prefix, len(pairs), threshold)

    set_progress(85, "Mengelompokkan cluster...")
    clusters = cluster_duplicates(pairs, video_ids, metadata=metadata_df)
    total_dupes = sum(c["cluster_size"] - 1 for c in clusters)
    if log_prefix:
        logger.info("✓ [%s]  88%%  %d clusters, %d duplicates", log_prefix, len(clusters), total_dupes)

    set_progress(90, "Membuat laporan Excel...")
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, "laporan_duplikat_konten.xlsx")
    analyzed_transcripts = {vid: transcripts[vid] for vid in video_ids if vid in transcripts}

    generate_report(
        output_path=excel_path,
        transcripts=analyzed_transcripts,
        clusters=clusters,
        metadata=metadata_df,
        similarity_matrix=sim_matrix,
        video_ids=video_ids,
        config={
            "channel_url": channel_url,
            "similarity_threshold": threshold,
            "use_stemming": use_stemming,
            "exclude_series": exclude_series,
        },
    )

    return {
        "clusters": clusters,
        "video_ids": video_ids,
        "transcripts": analyzed_transcripts,
        "excel_path": excel_path,
    }

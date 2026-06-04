import json
import os
import re
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisSummary,
    ClusterDetailEnriched,
    ClusterVideoEnriched,
    TranscriptPreview,
    generate_id,
    get_output_dir,
    get_subtitle_dir,
)
from backend.tasks import cancel_analysis, recompute_completed_analysis, run_analysis
from backend.database import Analysis

router = APIRouter()


@router.post("/analyses", response_model=AnalysisResponse)
def create_analysis(payload: AnalysisCreate, db: Session = Depends(get_db)):
    channel_url = payload.channel_url.strip()
    if not channel_url:
        raise HTTPException(status_code=422, detail="Channel URL wajib diisi")
    if payload.threshold < 0 or payload.threshold > 1:
        raise HTTPException(status_code=422, detail="Threshold harus berada di antara 0 dan 1")

    job_id = generate_id()

    analysis = Analysis(
        id=job_id,
        channel_url=channel_url,
        threshold=payload.threshold,
        use_stemming=int(payload.use_stemming),
        exclude_series=int(payload.exclude_series),
        audio_fallback=int(payload.audio_fallback),
        whisper_model=payload.whisper_model,
        status="running",
        progress=0,
        progress_message="Memulai...",
        subtitle_dir=get_subtitle_dir(job_id),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    run_analysis(
        job_id=job_id,
        channel_url=channel_url,
        threshold=payload.threshold,
        use_stemming=payload.use_stemming,
        exclude_series=payload.exclude_series,
        audio_fallback=payload.audio_fallback,
        whisper_model=payload.whisper_model,
    )

    return _to_response(analysis)


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(db: Session = Depends(get_db)):
    analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).all()
    return [_to_summary(a) for a in analyses]


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan")
    return _to_response(analysis)


@router.get("/analyses/{analysis_id}/clusters", response_model=list[ClusterDetailEnriched])
def get_clusters(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan")

    clusters_raw = json.loads(analysis.clusters_json) if analysis.clusters_json else []
    metadata_df = _load_metadata_if_exists(analysis.metadata_csv)

    enriched = []
    for cluster in clusters_raw:
        videos_enriched = []
        for v in cluster.get("videos", []):
            vid = v["video_id"]
            ev = ClusterVideoEnriched(
                video_id=vid,
                status=v["status"],
                similarity_to_primary=v["similarity_to_primary"],
                judul=_get_meta(metadata_df, vid, "judul", "N/A"),
                tanggal_publikasi=str(_get_meta(metadata_df, vid, "tanggal_publikasi", "N/A")),
                durasi=_get_meta(metadata_df, vid, "durasi", "N/A"),
                penayangan=_get_meta_int(metadata_df, vid, "penayangan", 0),
            )
            videos_enriched.append(ev)
        enriched.append(ClusterDetailEnriched(
            group_id=cluster["group_id"],
            videos=videos_enriched,
            avg_similarity=cluster["avg_similarity"],
            cluster_size=cluster["cluster_size"],
        ))

    return enriched


@router.get("/analyses/{analysis_id}/transcripts", response_model=list[TranscriptPreview])
def get_transcripts(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan")

    transcripts = json.loads(analysis.transcripts_json) if analysis.transcripts_json else {}
    result = []
    for vid in sorted(transcripts.keys()):
        text = transcripts[vid]
        preview = text[:200] + "..." if len(text) > 200 else text
        result.append(TranscriptPreview(video_id=vid, preview=preview))
    return result


@router.get("/analyses/{analysis_id}/download")
def download_excel(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis or not analysis.excel_path:
        raise HTTPException(status_code=404, detail="File Excel tidak ditemukan")

    if not os.path.exists(analysis.excel_path):
        raise HTTPException(status_code=404, detail="File Excel sudah dihapus")

    from fastapi.responses import FileResponse
    return FileResponse(
        analysis.excel_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"ytdupe_{analysis_id}.xlsx",
    )


@router.post("/analyses/{analysis_id}/metadata")
def upload_metadata(analysis_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan")
    if analysis.status != "completed":
        raise HTTPException(status_code=409, detail="Metadata hanya bisa diupload setelah analisis selesai")

    filename = _safe_csv_filename(file.filename)

    output_dir = get_output_dir(analysis_id)
    csv_path = os.path.join(output_dir, filename)
    with open(csv_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        recompute_completed_analysis(db, analysis_id, csv_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"message": "Metadata CSV berhasil diupload dan laporan diperbarui", "path": csv_path}


@router.post("/analyses/{analysis_id}/cancel")
def cancel_analysis_endpoint(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan")
    if analysis.status != "running":
        raise HTTPException(status_code=409, detail="Analisis tidak sedang berjalan")
    cancel_analysis(analysis_id)
    return {"message": "Analisis sedang dibatalkan"}


@router.delete("/analyses/{analysis_id}")
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis tidak ditemukan")
    if analysis.status == "running":
        raise HTTPException(status_code=409, detail="Analisis masih berjalan, batalkan terlebih dahulu")

    db.delete(analysis)
    db.commit()

    data_dir = os.path.join(os.environ.get("YTDUPE_DATA_DIR", "data"), analysis_id)
    shutil.rmtree(data_dir, ignore_errors=True)

    return {"message": "Analisis dihapus"}


def _to_response(a: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=a.id,
        channel_url=a.channel_url,
        channel_name=a.channel_name or "",
        status=a.status,
        progress=a.progress or 0,
        progress_message=a.progress_message or "",
        threshold=a.threshold or 0.75,
        total_videos=a.total_videos or 0,
        total_clusters=a.total_clusters or 0,
        total_duplicates=a.total_duplicates or 0,
        created_at=a.created_at,
        finished_at=a.finished_at,
    )


def _to_summary(a: Analysis) -> AnalysisSummary:
    return AnalysisSummary(
        id=a.id,
        channel_url=a.channel_url,
        channel_name=a.channel_name or "",
        status=a.status,
        total_videos=a.total_videos or 0,
        total_clusters=a.total_clusters or 0,
        total_duplicates=a.total_duplicates or 0,
        created_at=a.created_at,
        finished_at=a.finished_at,
    )


def _load_metadata_if_exists(csv_path: str):
    from ytdupe.utils import load_metadata
    if csv_path and os.path.exists(csv_path):
        return load_metadata(csv_path)
    return None


def _get_meta(metadata_df, video_id: str, field: str, default="N/A"):
    if metadata_df is None or metadata_df.empty:
        return default
    row = metadata_df[metadata_df["video_id"] == video_id]
    if row.empty:
        return default
    val = row.iloc[0].get(field, default)
    if val is None or (isinstance(val, float) and str(val) == "nan"):
        return default
    return val


def _get_meta_int(metadata_df, video_id: str, field: str, default: int = 0) -> int:
    val = _get_meta(metadata_df, video_id, field, None)
    if val is None or val == "N/A":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_csv_filename(filename: str | None) -> str:
    if not filename:
        return "metadata.csv"
    basename = os.path.basename(filename)
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._")
    if not safe:
        safe = "metadata.csv"
    if not safe.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="File metadata harus berformat CSV")
    return safe

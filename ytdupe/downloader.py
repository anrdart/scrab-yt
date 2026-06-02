import logging
import os
import sys

logger = logging.getLogger("ytdupe")


def download_subtitles(
    channel_url: str,
    lang_priority: list[str] | None = None,
    output_dir: str = "data/subtitles",
    sleep_interval: int = 2,
    on_progress: "callable[[int, int, str], None] | None" = None,
) -> dict:
    import yt_dlp

    if lang_priority is None:
        lang_priority = ["id", "en"]

    os.makedirs(output_dir, exist_ok=True)

    success_ids: list[str] = []
    failed: list[tuple[str, str]] = []

    playlist_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "logger": logging.getLogger("ytdupe.dlp"),
    }

    logger.info("Mengambil daftar video dari channel: %s", channel_url)
    try:
        with yt_dlp.YoutubeDL(playlist_opts) as ydl:
            playlist_info = ydl.extract_info(channel_url, download=False)
    except Exception as e:
        logger.error("Gagal mengambil daftar video: %s", e)
        return {"success": [], "failed": [("CHANNEL", str(e))]}

    entries = playlist_info.get("entries", []) or []
    video_entries = [e for e in entries if e and e.get("id") and e.get("_type") in ("video", "url")]

    logger.info("Ditemukan %d video. Memulai download subtitle...", len(video_entries))

    total = len(video_entries)
    for idx, entry in enumerate(video_entries, 1):
        video_id = entry["id"]
        downloaded = False

        if on_progress:
            on_progress(idx, total, video_id)

        for lang in lang_priority:
            outtmpl = os.path.join(output_dir, "%(id)s.%(ext)s")
            ydl_opts = {
                "writeautomaticsub": True,
                "subtitleslangs": [lang],
                "skip_download": True,
                "subformat": "vtt",
                "outtmpl": outtmpl,
                "sleep_interval": sleep_interval,
                "quiet": True,
                "no_warnings": True,
                "overwrites": True,
                "logger": logging.getLogger("ytdupe.dlp"),
                "retries": 1,
                "socket_timeout": 15,
            }

            try:
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                expected_vtt = os.path.join(output_dir, f"{video_id}.{lang}.vtt")
                fallback_vtt = os.path.join(output_dir, f"{video_id}.vtt")

                if os.path.exists(expected_vtt):
                    downloaded = True
                    break
                elif os.path.exists(fallback_vtt):
                    downloaded = True
                    break

            except Exception as e:
                logger.debug("Subtitle %s gagal untuk video %s: %s", lang, video_id, e)
                continue

        if downloaded:
            success_ids.append(video_id)
            logger.debug("Berhasil: %s", video_id)
        else:
            failed.append((video_id, "Tidak ada subtitle tersedia"))
            logger.debug("Gagal: %s — tidak ada subtitle", video_id)

    logger.info(
        "Selesai. Berhasil: %d, Gagal: %d", len(success_ids), len(failed)
    )
    return {"success": success_ids, "failed": failed}

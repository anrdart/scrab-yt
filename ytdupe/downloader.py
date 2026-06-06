import logging
import os
import re
import sys

logger = logging.getLogger("ytdupe")


def _resolve_uploads_url(channel_url: str) -> str:
    """Convert channel URL to uploads playlist URL for complete video listing."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlist_items": "1",
        "logger": logging.getLogger("ytdupe.dlp"),
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        channel_id = info.get("channel_id") or ""

    if channel_id.startswith("UC"):
        uploads_id = "UU" + channel_id[2:]
        return f"https://www.youtube.com/playlist?list={uploads_id}"

    return channel_url


def list_video_ids(channel_url: str, with_titles: bool = False) -> list[str] | list[dict]:
    import yt_dlp

    logger.info("Mengambil daftar video dari channel: %s", channel_url)
    try:
        resolved_url = _resolve_uploads_url(channel_url)
        logger.info("Resolved URL: %s", resolved_url)
    except Exception as e:
        logger.warning("Gagal resolve uploads URL, fallback ke URL asli: %s", e)
        resolved_url = channel_url

    playlist_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "logger": logging.getLogger("ytdupe.dlp"),
    }

    with yt_dlp.YoutubeDL(playlist_opts) as ydl:
        playlist_info = ydl.extract_info(resolved_url, download=False)

    entries = list(playlist_info.get("entries", []) or [])
    valid = [e for e in entries if e and e.get("id")]
    logger.info("Ditemukan %d video", len(valid))

    if with_titles:
        return [{"id": e["id"], "title": e.get("title", "")} for e in valid]
    return [e["id"] for e in valid]


def download_subtitles(
    channel_url: str,
    lang_priority: list[str] | None = None,
    output_dir: str = "data/subtitles",
    sleep_interval: int = 2,
    on_progress: "callable[[int, int, str], None] | None" = None,
) -> dict:
    if lang_priority is None:
        lang_priority = ["id", "en"]

    os.makedirs(output_dir, exist_ok=True)

    success_ids: list[str] = []
    failed: list[tuple[str, str]] = []

    try:
        video_entries = list_video_ids(channel_url)
    except Exception as e:
        logger.error("Gagal mengambil daftar video: %s", e)
        return {"success": [], "failed": [("CHANNEL", str(e))]}

    logger.info("Memulai download subtitle untuk %d video...", len(video_entries))

    total = len(video_entries)
    for idx, video_id in enumerate(video_entries, 1):
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

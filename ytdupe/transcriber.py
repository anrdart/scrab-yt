import logging
import os
import time
from typing import Callable

logger = logging.getLogger("ytdupe.worker")

_model = None


def _get_model(model_size: str = "small"):
    global _model
    if _model is None or _model._size != model_size:
        from faster_whisper import WhisperModel

        logger.info("Loading Whisper model '%s' (CPU, int8)...", model_size)
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        _model._size = model_size
    return _model


def _download_audio(video_id: str, audio_dir: str) -> str | None:
    import yt_dlp

    outtmpl = os.path.join(audio_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "worstaudio",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "retries": 2,
        "socket_timeout": 30,
        "logger": logger,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=True,
            )
            ext = info.get("ext", "webm")
            path = os.path.join(audio_dir, f"{video_id}.{ext}")
            if os.path.exists(path):
                return path
            for f in os.listdir(audio_dir):
                if f.startswith(video_id):
                    return os.path.join(audio_dir, f)
    except Exception as e:
        logger.warning("Audio download failed for %s: %s", video_id, e)

    return None


def transcribe_videos(
    video_ids: list[str],
    output_dir: str,
    audio_tmp_dir: str,
    model_size: str = "small",
    language: str = "id",
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, str]:
    if not video_ids:
        return {}

    os.makedirs(audio_tmp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    model = _get_model(model_size)
    results: dict[str, str] = {}
    total = len(video_ids)

    for idx, video_id in enumerate(video_ids, 1):
        audio_path = None
        try:
            if on_progress:
                on_progress(idx, total, video_id)

            audio_path = _download_audio(video_id, audio_tmp_dir)
            if not audio_path:
                logger.warning("No audio file for %s, skipping", video_id)
                continue

            segments, _info = model.transcribe(
                audio_path,
                language=language,
                beam_size=3,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments)

            if text.strip():
                txt_path = os.path.join(output_dir, f"{video_id}.whisper.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                results[video_id] = text
                logger.info("Transcribed %s (%d/%d)", video_id, idx, total)
            else:
                logger.warning("Empty transcription for %s", video_id)

        except Exception as e:
            logger.warning("Transcription failed for %s: %s", video_id, e)
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)

        time.sleep(1)

    logger.info("Audio transcription done: %d/%d successful", len(results), total)
    return results

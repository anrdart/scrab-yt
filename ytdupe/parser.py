import logging
import os
import re

logger = logging.getLogger("ytdupe")

TIMESTAMP_RE = re.compile(
    r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}"
)
TAG_RE = re.compile(r"<[^>]+>")
STYLEDirective_RE = re.compile(
    r"^(align|position|line|vertical|size|region):", re.IGNORECASE
)
SRT_SEQ_RE = re.compile(r"^\d+$")


def parse_vtt(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Gagal membaca file %s: %s", filepath, e)
        return ""

    clean_lines: list[str] = []
    prev_line = ""

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue
        if line == "WEBVTT":
            continue
        if line.startswith("NOTE"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if TIMESTAMP_RE.match(line):
            continue
        if STYLEDirective_RE.match(line):
            continue

        line = TAG_RE.sub("", line)
        line = line.strip()
        if not line:
            continue

        if line == prev_line:
            continue

        clean_lines.append(line)
        prev_line = line

    return " ".join(clean_lines)


def parse_srt(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Gagal membaca file %s: %s", filepath, e)
        return ""

    clean_lines: list[str] = []
    prev_line = ""

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue
        if SRT_SEQ_RE.match(line):
            continue
        if TIMESTAMP_RE.match(line):
            continue

        line = TAG_RE.sub("", line)
        line = line.strip()
        if not line:
            continue

        if line == prev_line:
            continue

        clean_lines.append(line)
        prev_line = line

    return " ".join(clean_lines)


def parse_subtitle(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".vtt":
        return parse_vtt(filepath)
    elif ext == ".srt":
        return parse_srt(filepath)
    else:
        logger.warning("Format tidak didukung: %s", filepath)
        return ""


def parse_all_subtitles(subtitle_dir: str) -> dict[str, str]:
    transcripts: dict[str, str] = {}

    if not os.path.isdir(subtitle_dir):
        logger.warning("Direktori subtitle tidak ditemukan: %s", subtitle_dir)
        return transcripts

    files = sorted(
        f
        for f in os.listdir(subtitle_dir)
        if f.endswith((".vtt", ".srt"))
    )

    for filename in files:
        filepath = os.path.join(subtitle_dir, filename)
        video_id = filename.split(".", 1)[0]

        text = parse_subtitle(filepath)
        if text.strip():
            transcripts[video_id] = text
        else:
            logger.warning("Transkrip kosong: %s", filename)

    logger.info("Berhasil parse %d transkrip dari %d file", len(transcripts), len(files))
    return transcripts

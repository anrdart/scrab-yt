import logging
import os

import pandas as pd
import yaml


DEFAULT_CONFIG = {
    "channel_url": "",
    "languages": ["id", "en"],
    "sleep_interval": 2,
    "similarity_threshold": 0.75,
    "use_stemming": False,
    "exclude_series": True,
    "output_file": "data/output/laporan_duplikat_konten.xlsx",
    "subtitle_dir": "data/subtitles",
}


def load_config(config_path: str = "config.yaml") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
        merged = {**DEFAULT_CONFIG, **file_config}
        return merged
    return dict(DEFAULT_CONFIG)


def setup_logging(log_file: str = "ytdupe.log") -> logging.Logger:
    logger = logging.getLogger("ytdupe")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)

    return logger


def ensure_dirs(config: dict):
    os.makedirs(config["subtitle_dir"], exist_ok=True)
    output_dir = os.path.dirname(config["output_file"])
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)


def load_metadata(csv_path: str) -> pd.DataFrame:
    columns = [
        "video_id",
        "judul",
        "tanggal_publikasi",
        "durasi",
        "penayangan",
        "waktu_tonton_jam",
        "subscriber",
        "tayangan",
        "rasio_klik_tayang",
    ]
    empty_df = pd.DataFrame(columns=columns)

    if not csv_path or not os.path.exists(csv_path):
        return empty_df

    df = None
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            return empty_df

    if df is None:
        return empty_df

    rename_map = {
        "Konten": "video_id",
        "Video ID": "video_id",
        "video id": "video_id",
        "Video Id": "video_id",
        "Judul video": "judul",
        "Judul": "judul",
        "Title": "judul",
        "Waktu publikasi video": "tanggal_publikasi",
        "Tanggal publikasi": "tanggal_publikasi",
        "Published": "tanggal_publikasi",
        "Durasi": "durasi",
        "Duration": "durasi",
        "Penayangan": "penayangan",
        "Views": "penayangan",
        "Waktu tonton (jam)": "waktu_tonton_jam",
        "Subscriber": "subscriber",
        "Tayangan": "tayangan",
        "Rasio klik-tayang dari tayangan (%)": "rasio_klik_tayang",
    }
    df = df.rename(columns=rename_map)

    if "video_id" not in df.columns:
        return empty_df

    df["video_id"] = df["video_id"].astype(str).str.strip()
    df = df[df["video_id"].ne("") & df["video_id"].ne("nan")]

    if "penayangan" not in df.columns:
        df["penayangan"] = 0

    if "penayangan" in df.columns:
        df["penayangan"] = (
            df["penayangan"]
            .astype(str)
            .str.replace(r"[^\d-]", "", regex=True)
            .str.strip()
        )
        df["penayangan"] = pd.to_numeric(df["penayangan"], errors="coerce").fillna(
            0
        ).astype(int)

    for col in columns:
        if col not in df.columns:
            df[col] = 0 if col == "penayangan" else ""

    df = df.sort_values("penayangan", ascending=False)
    df = df.drop_duplicates(subset=["video_id"], keep="first")

    return df[columns].reset_index(drop=True)


def parse_duration(durasi_str: str) -> int:
    if not durasi_str or not isinstance(durasi_str, str):
        return 0
    try:
        parts = durasi_str.strip().split(":")
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except (ValueError, IndexError):
        pass
    return 0

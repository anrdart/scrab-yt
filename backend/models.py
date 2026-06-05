import os
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnalysisCreate(BaseModel):
    channel_url: str
    threshold: float = 0.75
    use_stemming: bool = False
    exclude_series: bool = True
    audio_fallback: bool = True
    whisper_model: str = "small"
    mode: str = "duplicate"


class AnalysisResponse(BaseModel):
    id: str
    channel_url: str
    channel_name: str = ""
    status: str
    progress: int = 0
    progress_message: str = ""
    threshold: float = 0.75
    mode: str = "duplicate"
    total_videos: int = 0
    total_clusters: int = 0
    total_duplicates: int = 0
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClusterVideo(BaseModel):
    video_id: str
    status: str
    similarity_to_primary: float


class ClusterDetail(BaseModel):
    group_id: int
    videos: list[ClusterVideo]
    avg_similarity: float
    cluster_size: int


class ClusterVideoEnriched(ClusterVideo):
    judul: str = "N/A"
    tanggal_publikasi: str = "N/A"
    durasi: str = "N/A"
    penayangan: int = 0


class ClusterDetailEnriched(BaseModel):
    group_id: int
    videos: list[ClusterVideoEnriched]
    avg_similarity: float
    cluster_size: int


class TranscriptPreview(BaseModel):
    video_id: str
    preview: str


class AnalysisSummary(BaseModel):
    id: str
    channel_url: str
    channel_name: str = ""
    status: str
    mode: str = "duplicate"
    total_videos: int = 0
    total_clusters: int = 0
    total_duplicates: int = 0
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


def get_data_dir(analysis_id: str) -> str:
    base = os.environ.get("YTDUPE_DATA_DIR", "data")
    path = os.path.join(base, analysis_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_subtitle_dir(analysis_id: str) -> str:
    path = os.path.join(get_data_dir(analysis_id), "subtitles")
    os.makedirs(path, exist_ok=True)
    return path


def get_output_dir(analysis_id: str) -> str:
    path = os.path.join(get_data_dir(analysis_id), "output")
    os.makedirs(path, exist_ok=True)
    return path

import json
import os
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get("YTDUPE_DB", "ytdupe.db")

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True)
    channel_url = Column(String, nullable=False)
    channel_name = Column(String, default="")
    status = Column(String, default="pending")
    progress = Column(Integer, default=0)
    progress_message = Column(String, default="Menunggu...")
    threshold = Column(Float, default=0.75)
    use_stemming = Column(Integer, default=0)
    exclude_series = Column(Integer, default=1)
    total_videos = Column(Integer, default=0)
    total_clusters = Column(Integer, default=0)
    total_duplicates = Column(Integer, default=0)
    subtitle_dir = Column(String, default="")
    metadata_csv = Column(String, default="")
    excel_path = Column(String, default="")
    clusters_json = Column(Text, default="[]")
    transcripts_json = Column(Text, default="{}")
    video_ids_json = Column(Text, default="[]")
    mode = Column(String, default="duplicate")
    audio_fallback = Column(Integer, default=1)
    whisper_model = Column(String, default="small")
    audio_transcribed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE analyses ADD COLUMN mode TEXT DEFAULT 'duplicate'"))
            conn.commit()
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def update_analysis(db, analysis_id: str, **kwargs):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis:
        for key, value in kwargs.items():
            if hasattr(analysis, key):
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                setattr(analysis, key, value)
        db.commit()
        db.refresh(analysis)
    return analysis

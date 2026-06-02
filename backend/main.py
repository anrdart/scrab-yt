import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routes.api import router as api_router
from backend.routes.sse import router as sse_router

logger = logging.getLogger("ytdupe.app")

FORMAT = "%(asctime)s │ %(name)-18s │ %(message)s"
DATE_FORMAT = "%H:%M:%S"

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(FORMAT, datefmt=DATE_FORMAT))

for name in ("ytdupe", "ytdupe.app", "ytdupe.worker", "ytdupe.dlp"):
    logging.getLogger(name).handlers = [handler]
    logging.getLogger(name).propagate = False

logging.getLogger("ytdupe.app").setLevel(logging.INFO)
logging.getLogger("ytdupe.worker").setLevel(logging.INFO)
logging.getLogger("ytdupe").setLevel(logging.WARNING)
logging.getLogger("ytdupe.dlp").setLevel(logging.CRITICAL)

app = FastAPI(
    title="ytdupe API",
    description="API untuk deteksi duplikat konten YouTube",
    version="1.0.0",
)

cors_origins = [
    origin.strip()
    for origin in os.environ.get("YTDUPE_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(sse_router, prefix="/api")


@app.on_event("startup")
def startup():
    os.makedirs(os.environ.get("YTDUPE_DATA_DIR", "data"), exist_ok=True)
    init_db()
    logger.info("Backend started")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

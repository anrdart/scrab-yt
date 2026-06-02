FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    YTDUPE_DATA_DIR=/app/data \
    YTDUPE_DB=/app/data/ytdupe.db

WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY backend/requirements.txt ./backend-requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -r backend-requirements.txt

COPY backend ./backend
COPY ytdupe ./ytdupe

RUN mkdir -p /app/data

EXPOSE 8001

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8001}"]

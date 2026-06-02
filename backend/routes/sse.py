import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from backend.database import Analysis, SessionLocal

router = APIRouter()


@router.get("/analyses/{analysis_id}/stream")
def stream_progress(analysis_id: str):
    def event_generator():
        db = SessionLocal()
        last_payload = None
        try:
            while True:
                db.expire_all()
                analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
                if not analysis:
                    yield {"event": "error", "data": json.dumps({"error": "Not found"})}
                    break

                data = {
                    "progress": analysis.progress or 0,
                    "progress_message": analysis.progress_message or "",
                    "status": analysis.status,
                }
                payload = (data["progress"], data["progress_message"], data["status"])

                if payload != last_payload:
                    last_payload = payload
                    yield {"event": "progress", "data": json.dumps(data)}

                if analysis.status in ("completed", "failed"):
                    yield {"event": "done", "data": json.dumps({"status": analysis.status})}
                    break

                import time
                time.sleep(1)
        finally:
            db.close()

    return EventSourceResponse(event_generator())

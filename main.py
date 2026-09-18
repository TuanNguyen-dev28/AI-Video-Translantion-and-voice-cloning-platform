"""FastAPI service using PostgreSQL and Redis Queue for background processing."""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import redis
from rq import Queue

from config import AUTO_PUBLISH, BASE_DIR, OUTPUT_DIR, ensure_data_dir, REDIS_URL
from db import init_db, SessionLocal, JobModel, JobMessageModel
from worker import run_job, run_publish_sync

app = FastAPI(title="AI Video Translation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_conn = redis.from_url(REDIS_URL)
job_queue = Queue("video_jobs", connection=redis_conn)

@app.on_event("startup")
def startup():
    init_db()

class ProcessRequest(BaseModel):
    url: Optional[str] = ""
    voice_id: str = "default"
    background_music: str = "none"
    youtube_upload: bool = False
    facebook_upload: bool = False
    local_video_path: Optional[str] = None

@app.get("/api/health")
async def health() -> Dict:
    return {
        "status": "ok",
        "auto_publish": AUTO_PUBLISH,
        "queue_length": len(job_queue),
    }

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)) -> Dict[str, str]:
    """Store an input file locally using a generated, path-safe name."""
    suffix = Path(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    uploads_dir = ensure_data_dir() / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / f"{uuid.uuid4()}{suffix}"

    with open(file_path, "wb") as destination:
        while chunk := await file.read(1024 * 1024):
            destination.write(chunk)
    await file.close()

    return {"local_video_path": str(file_path.absolute())}


@app.post("/api/process")
async def process_video(request: ProcessRequest) -> Dict[str, object]:
    if not (request.url and request.url.strip()) and not request.local_video_path:
        raise HTTPException(status_code=422, detail="Provide url or local_video_path")

    job_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        job = JobModel(job_id=job_id, request_json=json.dumps(request.model_dump()))
        db.add(job)
        db.commit()
    finally:
        db.close()
        
    job_queue.enqueue(run_job, job_id, request.model_dump(), job_timeout=3600)

    return {
        "job_id": job_id,
        "status": "queued",
        "auto_publish": AUTO_PUBLISH,
    }


@app.post("/api/publish/{job_id}")
async def publish_video(job_id: str) -> Dict[str, str]:
    db = SessionLocal()
    try:
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
            
        result = json.loads(job.result_json) if job.result_json else {}
        if not result or not result.get("upload_pending"):
            raise HTTPException(status_code=400, detail="Job is not pending publish")
            
        request_data = json.loads(job.request_json)
        platforms = []
        if request_data.get("youtube_upload"):
            platforms.append("youtube")
        if request_data.get("facebook_upload"):
            platforms.append("facebook")
            
        if not platforms:
            raise HTTPException(status_code=400, detail="No platforms requested")

        # Enqueue manual publish job
        job_queue.enqueue(run_publish_sync, job_id, result, platforms, job_timeout=1800)
        return {"status": "publishing_queued"}
    finally:
        db.close()


@app.websocket("/ws/logs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    
    # 1. Send historical logs from DB
    db = SessionLocal()
    messages = db.query(JobMessageModel).filter(JobMessageModel.job_id == job_id).order_by(JobMessageModel.id).all()
    db.close()
    for msg in messages:
        await websocket.send_text(f"**{msg.step}**: {msg.message}")

    # 2. Subscribe to Redis for live logs
    pubsub = redis_conn.pubsub()
    pubsub.subscribe(f"logs:{job_id}")
    
    try:
        while True:
            # We use a non-blocking approach with asyncio
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message:
                text = message['data'].decode('utf-8')
                await websocket.send_text(text)
                if text.endswith("DONE_PIPELINE"):
                    break
            else:
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        pubsub.unsubscribe()


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> Dict:
    db = SessionLocal()
    try:
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job.job_id,
            "status": job.status,
            "request": json.loads(job.request_json),
            "result": json.loads(job.result_json) if job.result_json else None,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }
    finally:
        db.close()


@app.get("/api/video/{job_id}")
async def get_video(job_id: str) -> FileResponse:
    """Serve the dubbed video file for a completed job."""
    db = SessionLocal()
    try:
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        result = json.loads(job.result_json) if job.result_json else {}
    finally:
        db.close()
        
    if not result or not result.get("dubbed_video"):
        raise HTTPException(status_code=404, detail="Video not ready")

    video_path = Path(result["dubbed_video"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    try:
        video_path.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=video_path.name,
    )


# ---------------------------------------------------------------------------
# Serve the React frontend build
# ---------------------------------------------------------------------------
_frontend_dist = BASE_DIR / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

"""FastAPI service with a durable, single-host background job queue."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Dict, List, Optional
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import AUTO_PUBLISH, BASE_DIR, OUTPUT_DIR, WORKER_CONCURRENCY, ensure_data_dir
from pipeline import Pipeline
from modules.uploader import Uploader


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProcessRequest(BaseModel):
    url: Optional[str] = ""
    voice_id: str = "default"
    background_music: str = "none"
    youtube_upload: bool = False
    facebook_upload: bool = False
    local_video_path: Optional[str] = None


class JobStore:
    """Small SQLite persistence layer for the local worker queue."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    step TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
                );
                CREATE INDEX IF NOT EXISTS idx_job_messages_job_id
                    ON job_messages(job_id, id);
                """
            )

    def create_job(self, job_id: str, request: Dict) -> None:
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO jobs (job_id, status, request_json, created_at, updated_at)
                   VALUES (?, 'queued', ?, ?, ?)""",
                (job_id, json.dumps(request), now, now),
            )

    def set_status(self, job_id: str, status: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
                (status, _utc_now(), job_id),
            )

    def set_result(self, job_id: str, result: Dict) -> None:
        status = "completed" if result.get("success") else "failed"
        with self._connect() as connection:
            connection.execute(
                """UPDATE jobs SET status = ?, result_json = ?, updated_at = ?
                   WHERE job_id = ?""",
                (status, json.dumps(result, ensure_ascii=False), _utc_now(), job_id),
            )

    def add_message(self, job_id: str, step: str, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO job_messages (job_id, created_at, step, message)
                   VALUES (?, ?, ?, ?)""",
                (job_id, _utc_now(), step, message),
            )

    def get_job(self, job_id: str) -> Optional[Dict]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "job_id": row["job_id"],
            "status": row["status"],
            "request": json.loads(row["request_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_messages(self, job_id: str) -> List[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT step, message FROM job_messages
                   WHERE job_id = ? ORDER BY id""",
                (job_id,),
            ).fetchall()
        return [f"**{row['step']}**: {row['message']}" for row in rows]


class JobManager:
    """Persist jobs and fan out progress logs to active WebSocket clients."""

    def __init__(self) -> None:
        self.store = JobStore(ensure_data_dir() / "jobs.sqlite3")
        self.subscribers: Dict[str, List[asyncio.Queue[str]]] = {}
        self.lock = Lock()

    def create_job(self, request: ProcessRequest) -> str:
        job_id = str(uuid.uuid4())
        request_data = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        self.store.create_job(job_id, request_data)
        return job_id

    async def broadcast_log(self, job_id: str, step: str, message: str) -> None:
        self.store.add_message(job_id, step, message)
        entry = f"**{step}**: {message}"
        with self.lock:
            subscribers = list(self.subscribers.get(job_id, []))
        for queue in subscribers:
            queue.put_nowait(entry)

    def subscribe(self, job_id: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        with self.lock:
            self.subscribers.setdefault(job_id, []).append(queue)
        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue[str]) -> None:
        with self.lock:
            subscribers = self.subscribers.get(job_id, [])
            if queue in subscribers:
                subscribers.remove(queue)
            if not subscribers:
                self.subscribers.pop(job_id, None)


app = FastAPI(title="AI Video Translation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this before exposing the API to the internet.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_manager = JobManager()
worker_pool = ThreadPoolExecutor(
    max_workers=WORKER_CONCURRENCY,
    thread_name_prefix="video-worker",
)


def _target_platforms(request: ProcessRequest) -> List[str]:
    platforms: List[str] = []
    if request.youtube_upload:
        platforms.append("youtube")
    if request.facebook_upload:
        platforms.append("facebook")
    return platforms


def run_pipeline_sync(
    job_id: str, request: ProcessRequest, loop: asyncio.AbstractEventLoop
) -> None:
    """Run one queued pipeline on a worker thread."""
    job_manager.store.set_status(job_id, "running")

    def progress_callback(step: str, message: str) -> None:
        asyncio.run_coroutine_threadsafe(
            job_manager.broadcast_log(job_id, step, message), loop
        )

    try:
        result = Pipeline(output_callback=progress_callback).run(
            url=request.url or "",
            voice_id=request.voice_id,
            background_music=(
                "duck" if "duck" in request.background_music.lower() else "none"
            ),
            target_platforms=_target_platforms(request),
            local_video_path=request.local_video_path,
        )
    except Exception as exc:  # Pipeline normally returns errors; retain this guard.
        result = {"success": False, "error": str(exc)}

    job_manager.store.set_result(job_id, result)
    asyncio.run_coroutine_threadsafe(
        job_manager.broadcast_log(job_id, "SYSTEM", "DONE_PIPELINE"), loop
    )


@app.get("/api/health")
async def health() -> Dict:
    return {
        "status": "ok",
        "worker_concurrency": WORKER_CONCURRENCY,
        "auto_publish": AUTO_PUBLISH,
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

    job_id = job_manager.create_job(request)
    loop = asyncio.get_running_loop()
    worker_pool.submit(run_pipeline_sync, job_id, request, loop)
    return {
        "job_id": job_id,
        "status": "queued",
        "auto_publish": AUTO_PUBLISH,
    }


@app.post("/api/publish/{job_id}")
async def publish_video(job_id: str) -> Dict[str, str]:
    job = job_manager.store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = job.get("result")
    if not result or not result.get("upload_pending"):
        raise HTTPException(status_code=400, detail="Job is not pending publish")
        
    request_data = job.get("request", {})
    platforms = []
    if request_data.get("youtube_upload"):
        platforms.append("youtube")
    if request_data.get("facebook_upload"):
        platforms.append("facebook")
        
    if not platforms:
        raise HTTPException(status_code=400, detail="No platforms requested")

    loop = asyncio.get_running_loop()
    worker_pool.submit(run_publish_sync, job_id, result, platforms, loop)
    
    return {"status": "publishing_queued"}

def run_publish_sync(job_id: str, result: Dict, platforms: List[str], loop: asyncio.AbstractEventLoop) -> None:
    try:
        asyncio.run_coroutine_threadsafe(
            job_manager.broadcast_log(job_id, "STEP 9", f"Starting manual publish to {', '.join(platforms)}..."), loop
        )
        
        uploader = Uploader(Path(result["output_dir"]))
        upload_results = uploader.upload_all(
            Path(result["dubbed_video"]),
            result.get("metadata", {}),
            platforms,
        )
        
        result["youtube_url"] = upload_results.get("youtube", "")
        result["facebook_url"] = upload_results.get("facebook", "")
        result["upload_pending"] = False
        
        job_manager.store.set_result(job_id, result)
        
        asyncio.run_coroutine_threadsafe(
            job_manager.broadcast_log(job_id, "DONE", "Publish completed successfully."), loop
        )
    except Exception as exc:
        asyncio.run_coroutine_threadsafe(
            job_manager.broadcast_log(job_id, "ERROR", f"Publish failed: {exc}"), loop
        )

@app.websocket("/ws/logs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    if job_manager.store.get_job(job_id) is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    for message in job_manager.store.get_messages(job_id):
        await websocket.send_text(message)

    queue = job_manager.subscribe(job_id)
    try:
        while True:
            message = await queue.get()
            await websocket.send_text(message)
            if message.endswith("DONE_PIPELINE"):
                return
    except WebSocketDisconnect:
        return
    finally:
        job_manager.unsubscribe(job_id, queue)


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> Dict:
    job = job_manager.store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job["messages"] = job_manager.store.get_messages(job_id)
    return job


@app.get("/api/video/{job_id}")
async def get_video(job_id: str) -> FileResponse:
    """Serve the dubbed video file for a completed job."""
    job = job_manager.store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result = job.get("result")
    if not result or not result.get("dubbed_video"):
        raise HTTPException(status_code=404, detail="Video not ready")

    video_path = Path(result["dubbed_video"])
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    # Security: ensure the path is within the output directory
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
# Serve the React frontend build (must be mounted LAST so /api routes take
# precedence).  Run `npm run build` inside frontend/ to populate dist/.
# ---------------------------------------------------------------------------
_frontend_dist = BASE_DIR / "frontend" / "dist"
if _frontend_dist.is_dir():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="frontend-assets")

    # Catch-all: serve index.html for any non-API route (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        file_path = _frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

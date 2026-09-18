"""RQ Worker entry point for processing videos in the background."""
import json
import os
import redis
from rq import Worker, Queue, Connection
from config import REDIS_URL
from db import SessionLocal, JobModel, JobMessageModel, init_db
from pipeline import Pipeline

# Ensure database tables exist
init_db()

redis_conn = redis.from_url(REDIS_URL)

def run_job(job_id: str, request_dict: dict, target_platforms: list = None):
    """Executes the video pipeline."""
    db = SessionLocal()
    try:
        # Update status
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job:
            job.status = "running"
            db.commit()

        def progress_callback(step: str, message: str):
            # 1. Save to DB
            db_msg = JobMessageModel(job_id=job_id, step=step, message=message)
            db.add(db_msg)
            db.commit()
            
            # 2. Publish to Redis for WebSockets
            formatted = f"**{step}**: {message}"
            redis_conn.publish(f"logs:{job_id}", formatted)

        # Build platforms list
        platforms = target_platforms or []
        if not platforms:
            if request_dict.get("youtube_upload"):
                platforms.append("youtube")
            if request_dict.get("facebook_upload"):
                platforms.append("facebook")

        # Run pipeline
        pipeline = Pipeline(output_callback=progress_callback)
        result = pipeline.run(
            url=request_dict.get("url", ""),
            voice_id=request_dict.get("voice_id", "default"),
            background_music=request_dict.get("background_music", "none"),
            target_platforms=platforms,
            local_video_path=request_dict.get("local_video_path"),
        )
        
        # Save result
        job.status = "completed" if result.get("success") else "failed"
        job.result_json = json.dumps(result, ensure_ascii=False)
        db.commit()
        
        redis_conn.publish(f"logs:{job_id}", "**SYSTEM**: DONE_PIPELINE")

    except Exception as exc:
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.result_json = json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)
            db.commit()
            
        redis_conn.publish(f"logs:{job_id}", f"**ERROR**: {str(exc)}")
        redis_conn.publish(f"logs:{job_id}", "**SYSTEM**: DONE_PIPELINE")
    finally:
        db.close()


def run_publish_sync(job_id: str, result: dict, platforms: list):
    """Executes the manual publish action."""
    db = SessionLocal()
    try:
        def log_publish(step: str, message: str):
            db_msg = JobMessageModel(job_id=job_id, step=step, message=message)
            db.add(db_msg)
            db.commit()
            formatted = f"**{step}**: {message}"
            redis_conn.publish(f"logs:{job_id}", formatted)
            
        log_publish("STEP 9", f"Starting manual publish to {', '.join(platforms)}...")
        
        from modules.uploader import Uploader
        from pathlib import Path
        
        uploader = Uploader(Path(result["output_dir"]))
        upload_results = uploader.upload_all(
            Path(result["dubbed_video"]),
            result.get("metadata", {}),
            platforms,
        )
        
        result["youtube_url"] = upload_results.get("youtube", "")
        result["facebook_url"] = upload_results.get("facebook", "")
        result["upload_pending"] = False
        
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job:
            job.result_json = json.dumps(result, ensure_ascii=False)
            db.commit()
        
        log_publish("DONE", "Publish completed successfully.")

    except Exception as exc:
        log_publish("ERROR", f"Publish failed: {exc}")
    finally:
        db.close()


if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(['video_jobs'])
        print("Starting RQ worker...")
        worker.work()

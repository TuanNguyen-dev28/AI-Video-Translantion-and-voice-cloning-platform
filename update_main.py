import sys

path = r'e:\AI\AI Video Translantion and voice cloning platform\main.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

import_block_old = '''from config import AUTO_PUBLISH, BASE_DIR, OUTPUT_DIR, WORKER_CONCURRENCY, ensure_data_dir
from pipeline import Pipeline'''

import_block_new = '''from config import AUTO_PUBLISH, BASE_DIR, OUTPUT_DIR, WORKER_CONCURRENCY, ensure_data_dir
from pipeline import Pipeline
from modules.uploader import Uploader'''

if import_block_old in content:
    content = content.replace(import_block_old, import_block_new)

endpoint_block = '''@app.post("/api/publish/{job_id}")
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

'''

# Insert the endpoint right before the websocket endpoint
ws_endpoint_signature = '@app.websocket("/ws/logs/{job_id}")'
if ws_endpoint_signature in content and endpoint_block not in content:
    content = content.replace(ws_endpoint_signature, endpoint_block + ws_endpoint_signature)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated main.py")

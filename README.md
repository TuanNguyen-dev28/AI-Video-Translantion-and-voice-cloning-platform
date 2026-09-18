# AI Video Translation & Voice Cloning Platform

Local-first platform to download a video you are permitted to use, transcribe it, translate it to Vietnamese, generate dubbed audio, and optionally publish it through the platform's official APIs.

## What runs where

| Step | Default provider | Leaves this machine? |
| --- | --- | --- |
| Download / FFmpeg composition | `yt-dlp`, Playwright, FFmpeg | Connects to the source platform only |
| Speech-to-text | `faster-whisper` | No |
| Translation and metadata | Local OpenAI-compatible LLM | No |
| Text-to-speech | Edge TTS during transition | Yes; replace with your local TTS server when ready |
| YouTube / Facebook publishing | Official OAuth / Graph API | Yes; required for the selected account |

Cloud Groq and Gemini support remains only as an explicit compatibility fallback. It is disabled by default.

## Architecture

```text
Gradio / FastAPI -> SQLite-backed local queue -> GPU worker
                                             |-> local ASR
                                             |-> local LLM
                                             |-> TTS
                                             |-> FFmpeg
                                             `-> official upload APIs after approval
```

The FastAPI queue is durable across normal API requests: jobs, logs, and results are stored in `data/jobs.sqlite3`. The default worker concurrency is one, which prevents competing video jobs from exhausting a single GPU.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install FFmpeg and make sure both `ffmpeg` and `ffprobe` are on `PATH`.

## Configure the local bot

Copy `.env.example` to `.env`, then adjust it for your machine:

```powershell
Copy-Item .env.example .env
```

The first default run needs two local model services:

1. `faster-whisper` downloads `large-v3` on its first transcription. For a CPU-only computer, change `LOCAL_ASR_MODEL=small` in `.env`; it is slower and less accurate than a GPU setup.
2. Start a local LLM server. With Ollama, use `LOCAL_LLM_PROTOCOL=ollama` and load the model configured in `LOCAL_LLM_MODEL`. With vLLM, set `LOCAL_LLM_PROTOCOL=openai`, then update `LOCAL_LLM_BASE_URL` and `LOCAL_LLM_MODEL` to its server/model values.

The default settings are:

```env
ASR_PROVIDER=local
TEXT_PROVIDER=local
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_LLM_MODEL=qwen3:4b
LOCAL_LLM_PROTOCOL=ollama
LOCAL_LLM_THINKING=false
TTS_PROVIDER=edge
ALLOW_CLOUD_FALLBACK=false
AUTO_PUBLISH=false
```

`TTS_PROVIDER=edge` is intentionally retained as a bridge while you choose and validate a Vietnamese self-hosted TTS/voice-cloning model. When your local server exposes an OpenAI-compatible `POST /v1/audio/speech` endpoint that returns WAV audio, configure:

```env
TTS_PROVIDER=local
LOCAL_TTS_BASE_URL=http://127.0.0.1:PORT/v1
LOCAL_TTS_MODEL=your-vietnamese-tts-model
```

Only train or clone a voice with the speaker's documented consent and use source videos for which you have the necessary rights.

## Run

Start the visual interface:

```powershell
python app.py
```

Or start the API and local worker queue:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `GET /api/health` shows worker and auto-publish configuration.
- `POST /api/upload` stores a local input video safely.
- `POST /api/process` queues a process job.
- `GET /api/status/{job_id}` returns its persisted logs and result.
- `WS /ws/logs/{job_id}` streams progress logs.

## Publishing policy

`AUTO_PUBLISH=false` is the default. A completed job with YouTube/Facebook selected creates the dubbed video and metadata locally, then reports `upload_pending: true`; nothing is posted.

After review, set `AUTO_PUBLISH=true` and run a job for accounts you control. YouTube/Facebook access still requires their official OAuth/token flow; a local AI model cannot replace those account permissions.

## Optional cloud compatibility

Use this only when you deliberately allow media or transcript text to leave your machine:

```env
ALLOW_CLOUD_FALLBACK=true
ASR_PROVIDER=groq
TEXT_PROVIDER=gemini # or groq
```

Provide the matching key in `.env`. The local-first configuration does not need either key.

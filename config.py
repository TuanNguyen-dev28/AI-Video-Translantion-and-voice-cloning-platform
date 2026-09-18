"""
Configuration module for AI Video Translation Platform.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"

# Load environment variables from project .env file
load_dotenv(BASE_DIR / ".env")


# Database and Message Queue (used in Docker setup)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jobs.sqlite3")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
VIVIBE_API_KEY = os.getenv("VIVIBE_API_KEY", "")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")

# Service URLs
GROQ_BASE_URL = "https://api.groq.com/openai"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
VIVIBE_BASE_URL = "https://api.vivibe.ai/v1"

# Model configurations
WHISPER_MODEL = "whisper-large-v3"
TRANSLATION_MODEL_GEMINI = "gemini-2.0-flash"
TRANSLATION_MODEL_GROQ = "llama-3.3-70b-versatile"

# Self-hosted provider configuration.  The local services are the default so
# media and transcript text stay on this machine.  Set ALLOW_CLOUD_FALLBACK to
# true only when sending data to Groq/Gemini is an intentional fallback.
ASR_PROVIDER = os.getenv("ASR_PROVIDER", "local").strip().lower()
TEXT_PROVIDER = os.getenv("TEXT_PROVIDER", "local").strip().lower()
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge").strip().lower()
ALLOW_CLOUD_FALLBACK = os.getenv("ALLOW_CLOUD_FALLBACK", "false").strip().lower() in {
    "1", "true", "yes", "on"
}

# Local ASR (faster-whisper / CTranslate2).  "auto" uses CUDA when available
# and otherwise uses CPU int8 inference.
LOCAL_ASR_MODEL = os.getenv("LOCAL_ASR_MODEL", "large-v3")
LOCAL_ASR_DEVICE = os.getenv("LOCAL_ASR_DEVICE", "auto").strip().lower()
LOCAL_ASR_COMPUTE_TYPE = os.getenv("LOCAL_ASR_COMPUTE_TYPE", "auto").strip().lower()
LOCAL_ASR_LANGUAGE = os.getenv("LOCAL_ASR_LANGUAGE", "").strip() or None
LOCAL_ASR_VAD_FILTER = os.getenv("LOCAL_ASR_VAD_FILTER", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

# Local OpenAI-compatible LLM server, for example Ollama's /v1 endpoint or
# vLLM.  Set the model name to the model loaded by that server.
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen3:4b")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "")
LOCAL_LLM_PROTOCOL = os.getenv("LOCAL_LLM_PROTOCOL", "ollama").strip().lower()
LOCAL_LLM_THINKING = os.getenv("LOCAL_LLM_THINKING", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
LOCAL_LLM_TIMEOUT_SECONDS = float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "180"))
TRANSLATION_BATCH_SIZE = max(1, int(os.getenv("TRANSLATION_BATCH_SIZE", "25")))

# Optional self-hosted TTS server using the OpenAI-compatible /audio/speech
# endpoint.  Edge remains the compatibility default until a Vietnamese model
# has been selected and benchmarked.
LOCAL_TTS_BASE_URL = os.getenv("LOCAL_TTS_BASE_URL", "").rstrip("/")
LOCAL_TTS_MODEL = os.getenv("LOCAL_TTS_MODEL", "")
LOCAL_TTS_API_KEY = os.getenv("LOCAL_TTS_API_KEY", "")
LOCAL_TTS_TIMEOUT_SECONDS = float(os.getenv("LOCAL_TTS_TIMEOUT_SECONDS", "120"))

# Job worker and publishing policy.  AUTO_PUBLISH is deliberately opt-in:
# generated videos remain local until the owner explicitly enables publishing.
WORKER_CONCURRENCY = max(1, int(os.getenv("WORKER_CONCURRENCY", "1")))
AUTO_PUBLISH = os.getenv("AUTO_PUBLISH", "false").strip().lower() in {
    "1", "true", "yes", "on"
}

# TTS Settings
MAX_TTS_SPEED_MULTIPLIER = 1.3
DEFAULT_TTS_SPEED = 1.0
TEMPO_SLOWDOWN = 0.82  # atempo value for 18% slowdown

# Audio Settings
SAMPLE_RATE = 44100
AUDIO_FORMAT = "wav"
BACKGROUND_MUSIC_VOLUME_REDUCTION = -12  # dB

# Video Settings
VIDEO_FORMAT = "mp4"
DEFAULT_VIDEO_QUALITY = "best"

# YouTube OAuth
CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

# YouTube cookies file (Netscape format) for yt-dlp.
# Create this by exporting cookies from your browser (e.g. "Get cookies.txt LOCALLY" extension)
# and save the path here. When set, yt-dlp will use --cookies instead of --cookies-from-browser.
COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "")

# Platform detection patterns
PLATFORM_PATTERNS = {
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
    "douyin": ["douyin.com"],
}


def get_output_dir(timestamp: str) -> Path:
    """Get output directory for a specific job."""
    return OUTPUT_DIR / f"{timestamp}_v1"


def ensure_output_dir(timestamp: str) -> Path:
    """Ensure output directory exists."""
    out_dir = get_output_dir(timestamp)
    segments_dir = out_dir / "segments"
    out_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def ensure_data_dir() -> Path:
    """Ensure the local job database directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR

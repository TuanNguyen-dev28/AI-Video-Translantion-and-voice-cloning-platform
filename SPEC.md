# AI Video Translation & Voice Cloning Platform

## 1. Project Overview

**Project Name:** AI Video Translation & Voice Cloning Platform
**Type:** AI-powered Video Translation Web Application
**Core Functionality:** Tự động tải video từ YouTube/TikTok/Douyin, nhận dạng giọng nói, dịch sang tiếng Việt, tạo voice clone, và upload lên YouTube/Facebook.
**Target Users:** Content creators, marketers, streamers muốn localization video.

---

## 2. Technical Architecture

### 2.1 Project Structure

```
ai-video-translation/
├── app.py                    # Main Gradio UI
├── pipeline.py               # Main orchestrator
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── .env.example             # Environment template
├── output/                   # Output directory
│   └── {timestamp}_v1/
│       ├── original_video.mp4
│       ├── original_audio.wav
│       ├── no_vocals.wav     # Background music
│       ├── transcript_original.json
│       ├── transcript_original.srt
│       ├── transcript_vi.json
│       ├── segments/
│       │   ├── seg_001.wav ... seg_032.wav
│       ├── audio_vi_full.wav
│       ├── dubbed_video.mp4
│       ├── youtube_metadata.json
│       └── thumbnail_prompts.txt
├── modules/
│   ├── __init__.py
│   ├── video_downloader.py   # yt-dlp, Playwright
│   ├── audio_processor.py    # ffmpeg, demucs
│   ├── asr_transcriber.py    # Whisper
│   ├── translator.py         # Gemini, Groq
│   ├── tts_generator.py      # LucyLab/Vivibe
│   ├── audio_mixer.py        # Merge & timing
│   ├── video_composer.py     # ffmpeg compose
│   ├── metadata_generator.py # AI metadata
│   └── uploader.py           # YouTube, Facebook
├── utils/
│   ├── __init__.py
│   ├── file_utils.py
│   └── timing_utils.py
└── services/
    ├── __init__.py
    ├── groq_service.py
    ├── gemini_service.py
    └── vivibe_service.py
```

### 2.2 Technology Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Gradio |
| Video Download | yt-dlp, Playwright |
| Audio Processing | ffmpeg, Demucs |
| ASR | Groq Whisper (whisper-large-v3) |
| Translation | Gemini 2.0 Flash / Groq LLaMA 3.3 70B |
| TTS | LucyLab/Vivibe API |
| Video Composition | ffmpeg |
| YouTube Upload | Google OAuth2 |
| Facebook Upload | Graph API |

---

## 3. Pipeline Flow

### Step 1: Download Video
- **Input:** URL (YouTube/TikTok/Douyin)
- **Process:** 
  - YouTube/TikTok → yt-dlp
  - Douyin → Playwright
- **Output:** `original_video.mp4` in `output/{timestamp}_v1/`

### Step 2: Extract Audio
- **Process:** ffmpeg extract audio track
- **Output:** `original_audio.wav`

### Step 2.5: Background Music Processing
- **Options:** duck (reduce volume) or none
- **Process:** Demucs AI separation → vocal removal
- **Output:** `no_vocals.wav` (if duck selected)

### Step 3: ASR (Automatic Speech Recognition)
- **Model:** Groq Whisper large-v3
- **Output:**
  - `transcript_original.json` (32 segments with timestamps)
  - `transcript_original.srt`

### Step 4: Translation to Vietnamese
- **Primary:** Gemini 2.0 Flash
- **Fallback:** Groq LLaMA 3.3 70B
- **Output:** `transcript_vi.json` (with `text_vi` field added)

### Step 5: TTS Generation
- **Service:** LucyLab/Vivibe API
- **Process:** Auto-adjust speed (max 1.3x) to match original duration
- **Output:** `segments/seg_001.wav` ... `seg_032.wav`

### Step 6: Audio Mixing
- **6a:** Slow down 18% (atempo=0.82) if needed
- **6b:** Fit timeline - avoid segment overlaps
- **6c:** Merge all segments + background music
- **Output:** `audio_vi_full.wav`

### Step 7: Video Composition
- **Process:** ffmpeg merge video + Vietnamese audio
- **Output:** `dubbed_video.mp4`

### Step 8: Metadata Generation
- **Primary:** Gemini
- **Fallback:** Groq
- **Output:**
  - `youtube_metadata.json` (title, description, hashtags)
  - `thumbnail_prompts.txt`

### Step 9: Upload
- **YouTube:** OAuth2 with `client_secrets.json` → public
- **Facebook:** Graph API with Page token
- **Output:** Video URLs displayed on UI

---

## 4. UI Design

### 4.1 Interface Layout

```
┌─────────────────────────────────────────────────────────┐
│  AI VIDEO TRANSLATION & VOICE CLONING                   │
├─────────────────────────────────────────────────────────┤
│  [URL Input Field]                                      │
│                                                         │
│  Platform: ○ YouTube  ○ TikTok  ○ Douyin               │
│                                                         │
│  Voice Selection: [Dropdown with preview]               │
│                                                         │
│  Background Music: ○ Duck (-12dB)  ○ None              │
│                                                         │
│  Target Platform: □ YouTube  □ Facebook                 │
│                                                         │
│  [▶ RUN PIPELINE]                                       │
├─────────────────────────────────────────────────────────┤
│  Progress Log:                                          │
│  [  ] Step 1: Downloading video...                      │
│  [  ] Step 2: Extracting audio...                      │
│  [  ] Step 3: ASR transcription...                     │
│  [  ] Step 4: Translating...                           │
│  [  ] Step 5: Generating voice...                       │
│  [  ] Step 6: Mixing audio...                           │
│  [  ] Step 7: Composing video...                        │
│  [  ] Step 8: Generating metadata...                    │
│  [  ] Step 9: Uploading...                              │
├─────────────────────────────────────────────────────────┤
│  Result:                                                │
│  ▶ YouTube: https://youtube.com/watch?v=xxx            │
│  ▶ Facebook: https://facebook.com/xxx                 │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Color Palette
- **Primary:** #6366F1 (Indigo)
- **Secondary:** #8B5CF6 (Purple)
- **Accent:** #22D3EE (Cyan)
- **Background:** #0F172A (Dark Slate)
- **Surface:** #1E293B (Slate)
- **Text:** #F8FAFC (Light)
- **Success:** #22C55E (Green)
- **Error:** #EF4444 (Red)

---

## 5. API Keys Required

| Service | Purpose | Env Variable |
|---------|---------|--------------|
| Groq | Whisper ASR, LLaMA translation | GROQ_API_KEY |
| Gemini | Translation, Metadata | GEMINI_API_KEY |
| Vivibe | TTS voice cloning | VIVIBE_API_KEY |
| Google OAuth | YouTube upload | (client_secrets.json) |
| Facebook | Page upload | FB_PAGE_ACCESS_TOKEN |

---

## 6. Error Handling

- **Quota Exceeded:** Fallback to alternative service
- **Network Failure:** Retry with exponential backoff
- **Invalid URL:** Clear error message
- **Unsupported Format:** Skip with warning
- **Audio Sync Issues:** Automatic adjustment

---

## 7. Acceptance Criteria

- [ ] Can download video from YouTube, TikTok, Douyin
- [ ] Extracts clean audio track
- [ ] Generates accurate transcript with timestamps
- [ ] Translates to natural Vietnamese
- [ ] Creates matching TTS with original timing
- [ ] Mixes background music properly
- [ ] Outputs dubbed video
- [ ] Generates metadata for YouTube/Facebook
- [ ] Uploads successfully to both platforms
- [ ] Clean, responsive UI with progress tracking
- [ ] All API errors handled gracefully with fallbacks

"""Speech recognition with a local faster-whisper provider or Groq fallback."""
import json
from pathlib import Path
from typing import List, Dict, Optional

from config import ALLOW_CLOUD_FALLBACK, ASR_PROVIDER, GROQ_API_KEY, WHISPER_MODEL
from providers import LocalASRProvider


class ASRTranscriber:
    """Convert source audio to timestamped text without cloud by default."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.transcript_json_path: Optional[Path] = None
        self.transcript_srt_path: Optional[Path] = None
        self.segments: List[Dict] = []

    def transcribe(self, audio_path: Path) -> Dict:
        """
        Transcribe audio to text with timestamps.

        ``ASR_PROVIDER=local`` uses faster-whisper on this machine.  Groq is
        only selected explicitly or when ``ALLOW_CLOUD_FALLBACK=true``.

        Returns:
            Dictionary with segments containing text and timestamps
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        file_size = audio_path.stat().st_size
        if file_size < 1000:
            raise ValueError(f"Audio file too small ({file_size} bytes): {audio_path}")

        if ASR_PROVIDER == "local":
            try:
                self.segments = LocalASRProvider().transcribe(audio_path)
            except Exception as exc:
                if not ALLOW_CLOUD_FALLBACK:
                    raise RuntimeError(
                        "Local ASR failed. Fix the local faster-whisper setup or set "
                        "ALLOW_CLOUD_FALLBACK=true to intentionally use Groq."
                    ) from exc
                print(f"[ASR] Local ASR failed: {exc}; using Groq fallback")
                self.segments = self._transcribe_with_groq(audio_path)
        elif ASR_PROVIDER == "groq":
            self.segments = self._transcribe_with_groq(audio_path)
        else:
            raise ValueError("ASR_PROVIDER must be 'local' or 'groq'")

        self._save_json()
        self._save_srt()

        return {"segments": self.segments}

    def _transcribe_with_groq(self, audio_path: Path) -> List[Dict]:
        """Legacy cloud provider, kept for an explicit opt-in fallback."""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured")
        try:
            from groq import Groq
        except ImportError as exc:
            raise ImportError("Groq SDK not installed. Run: pip install groq") from exc

        client = Groq(api_key=GROQ_API_KEY)
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model=WHISPER_MODEL,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        return self._process_transcription(transcription)

    def _process_transcription(self, transcription) -> List[Dict]:
        """Process raw transcription into structured segments."""
        segments = []

        # Handle both dict and object response formats
        if isinstance(transcription, dict):
            seg_list = transcription.get("segments", [])
        else:
            seg_list = getattr(transcription, "segments", []) or []

        if seg_list:
            for idx, seg in enumerate(seg_list):
                if isinstance(seg, dict):
                    start = seg.get("start", 0)
                    end = seg.get("end", 0)
                    text = seg.get("text", "")
                else:
                    start = getattr(seg, "start", 0)
                    end = getattr(seg, "end", 0)
                    text = getattr(seg, "text", "")

                segments.append({
                    "id": idx,
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "text": text.strip(),
                })
        else:
            if isinstance(transcription, dict):
                text = transcription.get("text", "")
            else:
                text = getattr(transcription, "text", "")

            if text:
                segments.append({
                    "id": 0,
                    "start": 0.0,
                    "end": 0.0,
                    "duration": 0.0,
                    "text": text.strip(),
                })

        print(f"[ASR] Transcribed {len(segments)} segments")
        return segments

    def _save_json(self):
        """Save transcript as JSON with timestamps."""
        self.transcript_json_path = self.output_dir / "transcript_original.json"
        output = {
            "segments": self.segments,
            "total_segments": len(self.segments),
        }
        with open(self.transcript_json_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[ASR] Saved JSON to: {self.transcript_json_path}")

    def _save_srt(self):
        """Save transcript as SRT subtitle file."""
        self.transcript_srt_path = self.output_dir / "transcript_original.srt"
        with open(self.transcript_srt_path, "w", encoding="utf-8") as f:
            for idx, seg in enumerate(self.segments, 1):
                start_time = self._format_srt_time(seg["start"])
                end_time = self._format_srt_time(seg["end"])
                text = seg["text"]
                f.write(f"{idx}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
        print(f"[ASR] Saved SRT to: {self.transcript_srt_path}")

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds to SRT time format: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def get_segment_count(self) -> int:
        """Get total number of segments."""
        return len(self.segments)

    def release_resources(self) -> None:
        """Release local GPU memory; saved transcript data remains available."""
        if ASR_PROVIDER == "local":
            LocalASRProvider.release_cached_models()
            print("[LocalASR] Released local ASR model resources")

    def get_segment(self, index: int) -> Optional[Dict]:
        """Get specific segment by index."""
        if 0 <= index < len(self.segments):
            return self.segments[index]
        return None

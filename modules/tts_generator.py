"""TTS with an optional self-hosted provider and compatibility fallbacks."""
import subprocess
import struct
import wave
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

from config import (
    ALLOW_CLOUD_FALLBACK,
    VIVIBE_API_KEY,
    VIVIBE_BASE_URL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    MAX_TTS_SPEED_MULTIPLIER,
    SAMPLE_RATE,
    TTS_PROVIDER,
)
from providers import LocalTTSProvider


class TTSGenerator:
    """Generate Vietnamese speech locally when a compatible server is configured."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.segments_dir = output_dir / "segments"
        self.segments_dir.mkdir(exist_ok=True)
        self.segment_paths: List[Path] = []

    def generate(
        self,
        segments: List[Dict],
        voice_id: str = "vi-Female-1",
    ) -> List[Path]:
        """
        Generate TTS audio for each segment.

        Args:
            segments: List of segments with text_vi and timing info
            voice_id: Voice preset (vi-Female-1, vi-Male-1)

        Returns:
            List of generated audio file paths
        """
        self.segment_paths = []

        for seg in segments:
            text = seg.get("text_vi", seg.get("text", ""))
            segment_path = self._generate_segment(
                seg_id=seg["id"],
                text=text,
                original_duration=seg.get("duration", 0),
                voice_id=voice_id,
            )
            self.segment_paths.append(segment_path)

        print(f"[TTS] Generated {len(self.segment_paths)} segments")
        return self.segment_paths

    def _generate_segment(
        self,
        seg_id: int,
        text: str,
        original_duration: float,
        voice_id: str,
    ) -> Path:
        """Generate TTS for a single segment."""
        output_path = self.segments_dir / f"seg_{seg_id:03d}.wav"

        success = False

        if text.strip() and TTS_PROVIDER == "local":
            success = self._generate_local_tts(text, voice_id, output_path)
        elif text.strip() and TTS_PROVIDER == "edge":
            success = self._generate_edge_tts(text, voice_id, output_path)
        elif TTS_PROVIDER not in {"local", "edge", "cloud"}:
            raise ValueError("TTS_PROVIDER must be 'local', 'edge', or 'cloud'")

        # Cloud TTS is an explicit choice or an opted-in compatibility fallback.
        if not self._is_valid_wav(output_path) and (
            TTS_PROVIDER == "cloud" or ALLOW_CLOUD_FALLBACK
        ):
            success = self._generate_openai_compatible(text, voice_id, output_path)

        if (
            text.strip()
            and TTS_PROVIDER == "local"
            and not self._is_valid_wav(output_path)
            and not ALLOW_CLOUD_FALLBACK
        ):
            raise RuntimeError(
                "Local TTS did not generate audio. Configure LOCAL_TTS_BASE_URL and "
                "LOCAL_TTS_MODEL, or explicitly enable a cloud fallback."
            )

        # Final fallback: silence
        if not self._is_valid_wav(output_path):
            self._generate_fallback_tts(output_path, text, original_duration)

        # Adjust speed to match original timing
        tts_duration = self._get_audio_duration(output_path)
        if original_duration > 0.3 and tts_duration > 0:
            speed_mult = tts_duration / original_duration
            if 0.5 < speed_mult < 3.0:
                speed_mult = min(speed_mult, MAX_TTS_SPEED_MULTIPLIER)
                self._adjust_speed(output_path, speed_mult)
                final_dur = self._get_audio_duration(output_path)
                print(
                    f"[TTS] Seg {seg_id}: speed {speed_mult:.2f}x "
                    f"(orig={original_duration:.2f}s, tts={tts_duration:.2f}s, final={final_dur:.2f}s)"
                )
            elif speed_mult > MAX_TTS_SPEED_MULTIPLIER:
                # Text too long, need silence padding
                self._pad_to_duration(output_path, original_duration)

        return output_path

    def _generate_local_tts(self, text: str, voice_id: str, output_path: Path) -> bool:
        """Call the project's self-hosted OpenAI-compatible TTS endpoint."""
        try:
            LocalTTSProvider().synthesize(text, voice_id, output_path)
            if self._is_valid_wav(output_path):
                print(f"[TTS] Local TTS: {output_path.name}")
                return True
            print("[TTS] Local TTS did not return a valid WAV file")
        except Exception as exc:
            print(f"[TTS] Local TTS failed: {exc}")
        output_path.unlink(missing_ok=True)
        return False

    def _generate_edge_tts(self, text: str, voice_id: str, output_path: Path) -> bool:
        """Generate TTS using Microsoft Edge TTS (free, high quality)."""
        try:
            # Try module import first
            import edge_tts
            return self._edge_tts_generate(text, voice_id, output_path)
        except ImportError:
            # Fallback to subprocess using edge-tts CLI
            return self._edge_tts_subprocess(text, voice_id, output_path)
        except Exception as e:
            print(f"[TTS] Edge-TTS failed: {e}")
            return False

    def _edge_tts_generate(self, text: str, voice_id: str, output_path: Path) -> bool:
        """Generate using edge_tts Python module."""
        import edge_tts

        voice_map = {
            "vi-Female-1": "vi-VN-HoaiMyNeural",
            "vi-Female-2": "vi-VN-HoaiMyNeural",
            "vi-Male-1": "vi-VN-NamMinhNeural",
            "vi-Male-2": "vi-VN-NamMinhNeural",
            "default": "vi-VN-HoaiMyNeural",
        }
        voice = voice_map.get(voice_id, "vi-VN-HoaiMyNeural")

        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(str(output_path)))

        if self._is_valid_wav(output_path):
            print(f"[TTS] Edge-TTS: {output_path.name} ({output_path.stat().st_size} bytes)")
            return True
        return False

    def _edge_tts_subprocess(self, text: str, voice_id: str, output_path: Path) -> bool:
        """Generate using edge-tts CLI (fallback if module not importable)."""
        import shutil

        edge_tts_exe = shutil.which("edge-tts")
        if not edge_tts_exe:
            print("[TTS] edge-tts CLI not found in PATH")
            return False

        voice_map = {
            "vi-Female-1": "vi-VN-HoaiMyNeural",
            "vi-Female-2": "vi-VN-HoaiMyNeural",
            "vi-Male-1": "vi-VN-NamMinhNeural",
            "vi-Male-2": "vi-VN-NamMinhNeural",
            "default": "vi-VN-HoaiMyNeural",
        }
        voice = voice_map.get(voice_id, "vi-VN-HoaiMyNeural")

        # edge-tts outputs MP3, convert to WAV
        temp_mp3 = output_path.parent / f"temp_{output_path.stem}.mp3"
        cmd = [
            edge_tts_exe,
            "--voice", voice,
            "--text", text[:5000],
            "--write-media", str(temp_mp3),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            if temp_mp3.exists() and temp_mp3.stat().st_size > 1000:
                # Convert MP3 to WAV
                subprocess.run([
                    "ffmpeg", "-i", str(temp_mp3),
                    "-ar", str(SAMPLE_RATE),
                    "-ac", "1",
                    "-y", str(output_path),
                ], capture_output=True, check=True)
                temp_mp3.unlink(missing_ok=True)
                if self._is_valid_wav(output_path):
                    print(f"[TTS] Edge-TTS(CLI): {output_path.name}")
                    return True
        except Exception as e:
            print(f"[TTS] Edge-TTS CLI failed: {e}")
            output_path.unlink(missing_ok=True)
            temp_mp3.unlink(missing_ok=True)
        return False

    def _generate_openai_compatible(
        self, text: str, voice_id: str, output_path: Path
    ) -> bool:
        """Generate TTS using OpenAI-compatible API (Vivibe/Groq)."""
        import httpx

        providers = []

        if VIVIBE_API_KEY:
            providers.append({
                "name": "Vivibe",
                "api_key": VIVIBE_API_KEY,
                "base_url": VIVIBE_BASE_URL.rstrip("/"),
                "model": "vibevoice",
                "voice_map": {
                    "vi-Female-1": "female-vietnamese-1",
                    "vi-Male-1": "male-vietnamese-1",
                    "default": "alloy",
                },
            })

        if GROQ_API_KEY:
            providers.append({
                "name": "Groq",
                "api_key": GROQ_API_KEY,
                "base_url": GROQ_BASE_URL.rstrip("/"),
                "model": "playai-tts-2025-06-18",
                "voice_map": {
                    "vi-Female-1": "Shimmer",
                    "vi-Male-1": "Onyx",
                    "default": "alloy",
                },
            })

        for provider in providers:
            try:
                url = f"{provider['base_url']}/v1/audio/speech"
                headers = {
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json",
                }

                voice = provider["voice_map"].get(
                    voice_id, provider["voice_map"]["default"]
                )

                payload = {
                    "model": provider["model"],
                    "input": text[:5000],
                    "voice": voice,
                    "response_format": "wav",
                }

                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()

                with open(output_path, "wb") as f:
                    f.write(response.content)

                if self._is_valid_wav(output_path):
                    print(f"[TTS] {provider['name']}: {output_path.name}")
                    return True

            except Exception as e:
                print(f"[TTS] {provider['name']} failed: {e}")
                continue

        return False

    def _is_valid_wav(self, path: Path) -> bool:
        """Check if a WAV file is readable and has audio data."""
        if not path.exists() or path.stat().st_size < 100:
            return False
        try:
            with wave.open(str(path), "rb") as w:
                return w.getnframes() > 0
        except Exception:
            return False

    def _adjust_speed(self, audio_path: Path, speed: float):
        """Adjust audio speed using ffmpeg atempo filter."""
        if 0.5 <= speed <= 3.0:
            temp_path = audio_path.parent / f"temp_{audio_path.name}"
            cmd = [
                "ffmpeg", "-i", str(audio_path),
                "-af", f"atempo={speed}",
                "-ar", str(SAMPLE_RATE),
                "-y", str(temp_path),
            ]
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                temp_path.replace(audio_path)
            except subprocess.CalledProcessError as e:
                print(f"[TTS] Speed adjust failed: {e.stderr}")

    def _pad_to_duration(self, audio_path: Path, target_duration: float):
        """Pad audio with silence to reach target duration."""
        current = self._get_audio_duration(audio_path)
        if current >= target_duration:
            return

        temp_path = audio_path.parent / f"pad_{audio_path.name}"
        cmd = [
            "ffmpeg", "-i", str(audio_path),
            "-af", f"apad=whole_dur={target_duration}",
            "-t", str(target_duration),
            "-ar", str(SAMPLE_RATE),
            "-y", str(temp_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            temp_path.replace(audio_path)
        except subprocess.CalledProcessError as e:
            print(f"[TTS] Pad failed: {e.stderr}")

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        if not audio_path.exists():
            return 0.0
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _generate_fallback_tts(
        self, output_path: Path, text: str, duration: float = 3.0
    ):
        """Create a valid WAV silent file as fallback."""
        min_dur = max(len(text) / 20.0, 1.0)
        dur = max(min_dur, min(duration * 1.1, 10.0)) if duration > 0 else min_dur

        num_frames = int(SAMPLE_RATE * dur)
        data_size = num_frames * 2  # 16-bit mono

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1, SAMPLE_RATE,
            SAMPLE_RATE * 2, 2, 16,
            b"data", data_size,
        )
        try:
            with wave.open(str(output_path), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SAMPLE_RATE)
                w.writeframes(b"\x00" * data_size)
        except Exception:
            output_path.write_bytes(header + b"\x00" * data_size)
        print(f"[TTS] Fallback silence: {output_path.name} ({dur:.2f}s)")

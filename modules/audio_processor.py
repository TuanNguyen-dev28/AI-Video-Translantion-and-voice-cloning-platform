"""
Audio Processor Module - Extract audio and process background music.
Handles Step 2 (extract audio) and Step 2.5 (background music processing).
"""
import subprocess
from pathlib import Path
from typing import Literal, Optional

from config import (
    SAMPLE_RATE,
    AUDIO_FORMAT,
    BACKGROUND_MUSIC_VOLUME_REDUCTION,
)


class AudioProcessor:
    """Handles audio extraction and background music processing."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.audio_path: Optional[Path] = None
        self.no_vocals_path: Optional[Path] = None

    def extract_audio(self, video_path: Path) -> Path:
        """Extract audio from video using ffmpeg."""
        audio_path = self.output_dir / f"original_audio.{AUDIO_FORMAT}"

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(SAMPLE_RATE),
            "-ac", "2",
            "-y",
            str(audio_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"[Audio] Extracted audio to: {audio_path}")

            # Also create compressed version for API calls
            compressed_path = self._compress_for_api(audio_path)
            if compressed_path and compressed_path.exists():
                print(f"[Audio] Compressed for API: {compressed_path}")
                return compressed_path

            return audio_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")

    def _compress_for_api(self, audio_path: Path) -> Optional[Path]:
        """Compress audio to MP3 for API submission."""
        compressed_path = self.output_dir / "original_audio_compressed.mp3"

        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "32k",
            "-y",
            str(compressed_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return compressed_path
        except subprocess.CalledProcessError as e:
            print(f"[Audio] Compression failed: {e.stderr}")
            return None

    def process_background_music(
        self,
        audio_path: Path,
        option: Literal["duck", "none"],
    ) -> Optional[Path]:
        """Process background music using Demucs AI separation."""
        if option == "none":
            print("[Audio] Background music processing skipped (none)")
            return None

        try:
            return self._separate_vocals(audio_path)
        except Exception as e:
            print(f"[Audio] Background music processing failed: {e}")
            return None

    def _separate_vocals(self, audio_path: Path) -> Optional[Path]:
        """Separate vocals from audio using Demucs."""
        try:
            import torch
            from demucs.pretrained import get_model
            from demucs.audio import save_audio
            import torchaudio
        except ImportError:
            print("[Audio] Demucs not installed, skipping background separation")
            return None

        try:
            model = get_model("htdemucs")
            model.eval()

            waveform, sample_rate = torchaudio.load(str(audio_path))

            if waveform.shape[0] > 2:
                waveform = waveform[:2, :]

            if sample_rate != SAMPLE_RATE:
                resampler = torchaudio.transforms.Resample(sample_rate, SAMPLE_RATE)
                waveform = resampler(waveform)
                sample_rate = SAMPLE_RATE

            with torch.no_grad():
                sources = model(waveform.unsqueeze(0))

            # htdemucs sources: drums(0), bass(1), other(2), vocals(3)
            # Mix all non-vocal stems for complete instrumental track
            instrumental = sources[0, 0, :, :] + sources[0, 1, :, :] + sources[0, 2, :, :]

            no_vocals_path = self.output_dir / "no_vocals.wav"
            save_audio(
                instrumental,
                str(no_vocals_path),
                sample_rate=sample_rate,
            )

            if no_vocals_path.exists() and no_vocals_path.stat().st_size > 1000:
                self._apply_volume_reduction(no_vocals_path, BACKGROUND_MUSIC_VOLUME_REDUCTION)
                print(f"[Audio] Separated background music to: {no_vocals_path}")
                return no_vocals_path
            else:
                print("[Audio] Separation produced invalid file")
                return None

        except Exception as e:
            print(f"[Audio] Demucs separation failed: {e}")
            return None

    def _apply_volume_reduction(self, audio_path: Path, reduction_db: int):
        """Apply volume reduction in dB using ffmpeg."""
        import math
        volume_factor = 10 ** (reduction_db / 20)
        temp_path = self.output_dir / "temp_no_vocals.wav"

        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-af", f"volume={volume_factor}",
            "-y",
            str(temp_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            temp_path.replace(audio_path)
            print(f"[Audio] Applied {reduction_db}dB volume reduction")
        except subprocess.CalledProcessError as e:
            print(f"[Audio] Volume reduction failed: {e.stderr}")

    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

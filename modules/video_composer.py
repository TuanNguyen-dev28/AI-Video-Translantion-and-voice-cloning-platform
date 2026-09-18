"""
Video Composer Module - Combine video with dubbed audio.
Handles Step 7: Merge original video with Vietnamese audio.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from config import VIDEO_FORMAT, SAMPLE_RATE


class VideoComposer:
    """Handles video composition: merging video with dubbed audio."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.dubbed_video_path: Optional[Path] = None

    def compose(self, video_path: Path, audio_path: Path) -> Path:
        """
        Compose dubbed video by merging original video with Vietnamese audio.

        Args:
            video_path: Path to original video
            audio_path: Path to dubbed Vietnamese audio

        Returns:
            Path to final dubbed video
        """
        output_path = self.output_dir / f"dubbed_video.{VIDEO_FORMAT}"
        ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        cmd = [
            ffmpeg_path,
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-y",
            str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.dubbed_video_path = output_path
            print(f"[Composer] Created dubbed video: {output_path}")
            return output_path

        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and add it to PATH. "
                "Download from: https://ffmpeg.org/download.html"
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            raise RuntimeError(f"Video composition failed: {error_msg}")

    def compose_with_reencode(
        self,
        video_path: Path,
        audio_path: Path,
        quality: str = "medium",
    ) -> Path:
        """Compose video with re-encoding for better compatibility."""
        output_path = self.output_dir / f"dubbed_video_{quality}.{VIDEO_FORMAT}"
        ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"

        quality_presets = {
            "low": {"crf": 28, "preset": "veryfast"},
            "medium": {"crf": 23, "preset": "medium"},
            "high": {"crf": 18, "preset": "slow"},
        }

        preset = quality_presets.get(quality, quality_presets["medium"])

        cmd = [
            ffmpeg_path,
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-crf", str(preset["crf"]),
            "-preset", preset["preset"],
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", str(SAMPLE_RATE),
            "-shortest",
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            self.dubbed_video_path = output_path
            print(f"[Composer] Created re-encoded video: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Video re-encoding failed: {e.stderr}")

    def get_video_duration(self, video_path: Path) -> float:
        """Get duration of video file in seconds."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0.0

    def get_video_info(self, video_path: Path) -> dict:
        """Get video information."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(video_path),
        ]
        try:
            import json
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except Exception:
            return {}

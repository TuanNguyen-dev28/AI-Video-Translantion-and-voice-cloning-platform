"""
Audio Mixer Module - Merge segments and mix with background music.
Handles Step 6: Audio mixing with timeline fitting and speed adjustment.
"""
import subprocess
import wave
from pathlib import Path
from typing import List, Dict, Optional

from config import (
    TEMPO_SLOWDOWN,
    SAMPLE_RATE,
)


class AudioMixer:
    """Handles audio mixing: segment merging and background music integration."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.segments_dir = output_dir / "segments"
        self.final_audio_path: Optional[Path] = None

    def mix(
        self,
        segments: List[Dict],
        segment_paths: List[Path],
        background_music_path: Optional[Path] = None,
        needs_slowdown: bool = False,
    ) -> Path:
        """
        Mix all audio segments with optional background music.

        Args:
            segments: List of segment metadata
            segment_paths: List of generated TTS audio paths
            background_music_path: Path to background music (no_vocals.wav)
            needs_slowdown: Apply 18% slowdown (atempo=0.82)

        Returns:
            Path to final mixed audio
        """
        # Filter valid paths
        valid_paths = [p for p in segment_paths if p.exists() and self._is_valid_wav(p)]

        if not valid_paths:
            raise RuntimeError("No valid audio segments to merge")

        # Apply slowdown if needed
        if needs_slowdown:
            valid_paths = self._apply_slowdown(valid_paths)

        # Merge segments
        merged_path = self._merge_segments_filtered(valid_paths)

        # Mix with background music
        if background_music_path and background_music_path.exists() and self._is_valid_wav(background_music_path):
            final_path = self._mix_with_background(merged_path, background_music_path)
        else:
            final_path = merged_path

        self.final_audio_path = final_path
        return final_path

    def _apply_slowdown(self, segment_paths: List[Path]) -> List[Path]:
        """Apply 18% slowdown (tempo=0.82) to all segments."""
        slowed_paths = []
        for path in segment_paths:
            slowed_path = path.parent / f"slowed_{path.name}"
            cmd = [
                "ffmpeg",
                "-i", str(path),
                "-af", f"atempo={TEMPO_SLOWDOWN}",
                "-ar", str(SAMPLE_RATE),
                "-y",
                str(slowed_path),
            ]
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                slowed_paths.append(slowed_path)
                print(f"[Mixer] Slowed: {path.name}")
            except subprocess.CalledProcessError as e:
                print(f"[Mixer] Slowdown failed for {path.name}: {e.stderr}")
                slowed_paths.append(path)
        return slowed_paths

    def _is_valid_wav(self, path: Path) -> bool:
        """Check if a WAV file is readable and has valid audio content."""
        if not path.exists() or path.stat().st_size < 44:
            return False
        try:
            with wave.open(str(path), "rb") as w:
                n_frames = w.getnframes()
                n_channels = w.getnchannels()
                sampwidth = w.getsampwidth()
                return n_frames > 0 and n_channels >= 1 and sampwidth >= 1
        except Exception:
            return False

    def _merge_segments_filtered(self, segment_paths: List[Path]) -> Path:
        """Merge valid segment audio files into one using ffmpeg concat demuxer."""
        merged_path = self.output_dir / "merged_segments.wav"

        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for path in segment_paths:
                f.write(f"file '{path.absolute()}'\n")

        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-acodec", "pcm_s16le",
            "-ar", str(SAMPLE_RATE),
            "-ac", "2",
            "-y",
            str(merged_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"[Mixer] Merged {len(segment_paths)} segments -> {merged_path.name}")
            return merged_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Segment merge failed: {e.stderr}")

    def _mix_with_background(
        self,
        main_audio_path: Path,
        background_path: Path,
    ) -> Path:
        """Mix main audio with background music."""
        final_path = self.output_dir / "audio_vi_full.wav"

        main_duration = self._get_audio_duration(main_audio_path)
        bg_duration = self._get_audio_duration(background_path)

        if bg_duration < main_duration:
            looped_bg = self._loop_background(background_path, main_duration)
        else:
            looped_bg = background_path

        cmd = [
            "ffmpeg",
            "-i", str(main_audio_path),
            "-i", str(looped_bg),
            "-filter_complex",
            "[1:a]volume=0.3[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "[a]",
            "-ar", str(SAMPLE_RATE),
            "-y",
            str(final_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print("[Mixer] Mixed with background music")
            return final_path
        except subprocess.CalledProcessError as e:
            print(f"[Mixer] Mix failed: {e.stderr}, using main audio only")
            return main_audio_path

    def _loop_background(
        self,
        background_path: Path,
        target_duration: float,
    ) -> Path:
        """Loop background audio to match target duration."""
        looped_path = self.output_dir / "background_looped.wav"
        cmd = [
            "ffmpeg",
            "-stream_loop", "-1",
            "-i", str(background_path),
            "-t", str(target_duration),
            "-acodec", "pcm_s16le",
            "-y",
            str(looped_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return looped_path
        except subprocess.CalledProcessError:
            return background_path

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of audio file in seconds."""
        if not audio_path.exists():
            return 0.0
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
        except (subprocess.CalledProcessError, ValueError):
            return 0.0

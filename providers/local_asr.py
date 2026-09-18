"""Local speech-to-text adapter backed by faster-whisper."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Dict, List

from config import (
    LOCAL_ASR_COMPUTE_TYPE,
    LOCAL_ASR_DEVICE,
    LOCAL_ASR_LANGUAGE,
    LOCAL_ASR_MODEL,
    LOCAL_ASR_VAD_FILTER,
)


class LocalASRProvider:
    """Run Whisper locally without uploading audio to an external API."""

    _models: Dict[tuple[str, str, str], object] = {}

    def __init__(
        self,
        model_name: str = LOCAL_ASR_MODEL,
        device: str = LOCAL_ASR_DEVICE,
        compute_type: str = LOCAL_ASR_COMPUTE_TYPE,
        language: str | None = LOCAL_ASR_LANGUAGE,
        vad_filter: bool = LOCAL_ASR_VAD_FILTER,
    ):
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.compute_type = self._resolve_compute_type(compute_type, self.device)
        self.language = language
        self.vad_filter = vad_filter

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda"
        except (ImportError, RuntimeError):
            pass
        return "cpu"

    @staticmethod
    def _resolve_compute_type(compute_type: str, device: str) -> str:
        if compute_type != "auto":
            return compute_type
        # This substantially lowers VRAM use on a CUDA machine while preserving
        # FP16 activations. It leaves room for the local LLM on an 8 GB GPU.
        return "int8_float16" if device == "cuda" else "int8"

    @classmethod
    def release_cached_models(cls) -> None:
        """Release ASR model references once transcription has completed."""
        cls._models.clear()
        gc.collect()

    @property
    def model(self):
        key = (self.model_name, self.device, self.compute_type)
        if key not in self._models:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ImportError(
                    "faster-whisper is not installed. Run: pip install -r requirements.txt"
                ) from exc

            print(
                "[LocalASR] Loading "
                f"{self.model_name} on {self.device} ({self.compute_type})..."
            )
            self._models[key] = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._models[key]

    def transcribe(self, audio_path: Path) -> List[Dict]:
        """Return pipeline-compatible segments with timestamps."""
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if audio_path.stat().st_size < 1000:
            raise ValueError(f"Audio file too small: {audio_path}")

        kwargs = {
            "language": self.language,
            "vad_filter": self.vad_filter,
            "word_timestamps": False,
        }
        raw_segments, info = self.model.transcribe(str(audio_path), **kwargs)
        detected_language = getattr(info, "language", "unknown")
        print(f"[LocalASR] Detected language: {detected_language}")

        segments: List[Dict] = []
        for index, segment in enumerate(raw_segments):
            text = (getattr(segment, "text", "") or "").strip()
            if not text:
                continue
            start = float(getattr(segment, "start", 0.0))
            end = float(getattr(segment, "end", start))
            segments.append(
                {
                    "id": index,
                    "start": start,
                    "end": end,
                    "duration": max(0.0, end - start),
                    "text": text,
                }
            )

        print(f"[LocalASR] Transcribed {len(segments)} segments")
        return segments

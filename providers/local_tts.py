"""Client for an optional self-hosted OpenAI-compatible TTS server."""

from __future__ import annotations

from pathlib import Path

import httpx

from config import (
    LOCAL_TTS_API_KEY,
    LOCAL_TTS_BASE_URL,
    LOCAL_TTS_MODEL,
    LOCAL_TTS_TIMEOUT_SECONDS,
)


class LocalTTSProvider:
    """Synthesize speech without sending text to a third-party TTS API."""

    def __init__(
        self,
        base_url: str = LOCAL_TTS_BASE_URL,
        model: str = LOCAL_TTS_MODEL,
        api_key: str = LOCAL_TTS_API_KEY,
        timeout_seconds: float = LOCAL_TTS_TIMEOUT_SECONDS,
    ):
        if not base_url:
            raise ValueError("LOCAL_TTS_BASE_URL is not configured")
        if not model:
            raise ValueError("LOCAL_TTS_MODEL is not configured")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def synthesize(self, text: str, voice: str, output_path: Path) -> None:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "input": text[:5000],
            "voice": voice,
            "response_format": "wav",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/audio/speech",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "Local TTS request failed. Confirm the server is running and "
                f"LOCAL_TTS_BASE_URL is correct: {self.base_url}"
            ) from exc

        output_path.write_bytes(response.content)

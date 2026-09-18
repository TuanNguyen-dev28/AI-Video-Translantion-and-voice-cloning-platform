"""
Vivibe/LucyLab TTS API Service.
"""
from typing import Optional
from pathlib import Path

import httpx

from config import VIVIBE_API_KEY, VIVIBE_BASE_URL


class VivibeService:
    """Service wrapper for Vivibe TTS API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or VIVIBE_API_KEY
        self.base_url = VIVIBE_BASE_URL
        self._available_voices: Optional[list] = None

    def generate_speech(
        self,
        text: str,
        voice_id: str = "default",
        language: str = "vi",
        output_path: Optional[Path] = None,
    ) -> bytes:
        """
        Generate speech from text.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use
            language: Language code
            output_path: Optional path to save audio
            
        Returns:
            Audio bytes
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "text": text,
            "voice_id": voice_id,
            "language": language,
            "output_format": "wav",
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/tts",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        audio_bytes = response.content

        if output_path:
            output_path.write_bytes(audio_bytes)

        return audio_bytes

    def get_available_voices(self) -> list:
        """Get list of available voices."""
        if self._available_voices is None:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{self.base_url}/voices",
                    headers=headers,
                )

                if response.status_code == 200:
                    self._available_voices = response.json().get("voices", [])
                else:
                    self._available_voices = []

        return self._available_voices

    def list_vietnamese_voices(self) -> list:
        """List Vietnamese voices only."""
        voices = self.get_available_voices()
        return [v for v in voices if v.get("language", "").startswith("vi")]

    def generate_segment(
        self,
        text: str,
        voice_id: str,
        target_duration: float,
        max_speed: float = 1.3,
    ) -> bytes:
        """
        Generate speech with speed adjustment for target duration.
        
        Args:
            text: Text to speak
            voice_id: Voice to use
            target_duration: Target duration in seconds
            max_speed: Maximum speed multiplier
            
        Returns:
            Audio bytes
        """
        audio = self.generate_speech(text, voice_id)

        # Note: Speed adjustment should be done externally using ffmpeg
        # This method returns raw audio - caller should adjust speed as needed
        return audio

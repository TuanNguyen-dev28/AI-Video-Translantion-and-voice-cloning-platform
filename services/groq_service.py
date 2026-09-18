"""
Groq API Service - Whisper ASR and LLaMA translation.
"""
from typing import Optional, List, Dict
from pathlib import Path

from config import GROQ_API_KEY, GROQ_BASE_URL, WHISPER_MODEL, TRANSLATION_MODEL_GROQ


class GroqService:
    """Service wrapper for Groq API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GROQ_API_KEY
        self.base_url = GROQ_BASE_URL
        self._client = None

    @property
    def client(self):
        """Lazy load Groq client."""
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise ImportError("Groq SDK not installed: pip install groq")
        return self._client

    def transcribe_audio(
        self,
        audio_path: Path,
        language: str = "auto",
    ) -> Dict:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_path: Path to audio file
            language: Source language (auto for detection)
            
        Returns:
            Transcription result with segments
        """
        with open(audio_path, "rb") as f:
            transcription = self.client.audio.transcriptions.create(
                file=f,
                model=WHISPER_MODEL,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                language=language if language != "auto" else None,
            )
        return transcription

    def translate_text(
        self,
        text: str,
        target_language: str = "vi",
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Translate text using LLaMA.
        
        Args:
            text: Text to translate
            target_language: Target language code
            system_prompt: Optional system prompt
            
        Returns:
            Translated text
        """
        system = system_prompt or (
            "You are a professional translator. Translate accurately to Vietnamese "
            "while maintaining natural speech patterns."
        )

        prompt = f"""Translate the following text to {target_language}:
{text}"""

        response = self.client.chat.completions.create(
            model=TRANSLATION_MODEL_GROQ,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return response.choices[0].message.content

    def batch_translate(
        self,
        segments: List[Dict],
        text_field: str = "text",
        output_field: str = "text_vi",
    ) -> List[Dict]:
        """
        Translate a batch of segments.
        
        Args:
            segments: List of segment dicts
            text_field: Field containing text to translate
            output_field: Field to store translation
            
        Returns:
            Segments with translations added
        """
        results = []
        for seg in segments:
            text = seg.get(text_field, "")
            if text:
                translated = self.translate_text(text)
                new_seg = seg.copy()
                new_seg[output_field] = translated
                results.append(new_seg)
            else:
                results.append(seg)
        return results

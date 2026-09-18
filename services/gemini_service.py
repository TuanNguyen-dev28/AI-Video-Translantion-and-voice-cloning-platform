"""
Gemini API Service - Translation and metadata generation.
"""
from typing import Optional, List, Dict

from config import GEMINI_API_KEY, TRANSLATION_MODEL_GEMINI


class GeminiService:
    """Service wrapper for Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self._client = None

    @property
    def client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            try:
                import google.genai as genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError("Google GenAI not installed: pip install google-genai")
        return self._client

    def translate_text(
        self,
        text: str,
        target_language: str = "Vietnamese",
    ) -> str:
        """
        Translate text using Gemini.
        
        Args:
            text: Text to translate
            target_language: Target language name
            
        Returns:
            Translated text
        """
        prompt = f"""Translate the following text to {target_language}.
Maintain natural speech patterns and meaning.
Keep names and technical terms in original language if appropriate.

Text to translate:
{text}"""

        response = self.client.models.generate_content(
            model=TRANSLATION_MODEL_GEMINI,
            contents=prompt,
        )

        return response.text

    def translate_segments(
        self,
        segments: List[Dict],
        text_field: str = "text",
        output_field: str = "text_vi",
    ) -> List[Dict]:
        """
        Translate multiple segments at once.
        
        Args:
            segments: List of segment dicts
            text_field: Field containing text
            output_field: Field to store translation
            
        Returns:
            Segments with translations
        """
        # Prepare batch prompt
        text_to_translate = "\n".join(
            f"[{i}] {seg.get(text_field, '')}"
            for i, seg in enumerate(segments)
        )

        prompt = f"""Translate the following segments to Vietnamese.
Return ONLY valid JSON in this format:
{{"translations": [{{"id": 0, "text_vi": "..."}}, ...]}}

Keep translations concise and natural.

Segments:
{text_to_translate}"""

        response = self.client.models.generate_content(
            model=TRANSLATION_MODEL_GEMINI,
            contents=prompt,
        )

        # Parse translations
        try:
            import json
            json_str = self._extract_json(response.text)
            data = json.loads(json_str)
            translations = {t["id"]: t["text_vi"] for t in data.get("translations", [])}
        except Exception:
            translations = {}

        # Apply translations
        results = []
        for seg in segments:
            new_seg = seg.copy()
            seg_id = seg.get("id", 0)
            new_seg[output_field] = translations.get(seg_id, seg.get(text_field, ""))
            results.append(new_seg)

        return results

    def generate_metadata(
        self,
        content_summary: str,
        original_title: str = "",
    ) -> Dict:
        """
        Generate YouTube/Facebook metadata.
        
        Args:
            content_summary: Summary of video content
            original_title: Original video title
            
        Returns:
            Metadata dict with title, description, hashtags
        """
        prompt = f"""Based on the video content, generate metadata for YouTube and Facebook.

Original title: {original_title or "N/A"}

Generate in JSON format:
{{
    "title": "Catchy Vietnamese title (max 100 chars)",
    "description": "Description in Vietnamese (max 5000 chars)",
    "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "thumbnail_prompt": "Thumbnail generation description"
}}

Video content:
{content_summary}"""

        response = self.client.models.generate_content(
            model=TRANSLATION_MODEL_GEMINI,
            contents=prompt,
        )

        # Parse response
        try:
            import json
            json_str = self._extract_json(response.text)
            return json.loads(json_str)
        except Exception:
            return {
                "title": "Video đã dịch",
                "description": "Video được dịch tự động bằng AI",
                "hashtags": ["ai", "translation", "vietnamese"],
                "thumbnail_prompt": "Professional video thumbnail",
            }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        return text.strip()

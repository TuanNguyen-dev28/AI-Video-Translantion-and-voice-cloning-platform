"""Generate social metadata with a self-hosted LLM by default."""
import json
from pathlib import Path
from typing import Dict, Optional

from config import (
    ALLOW_CLOUD_FALLBACK,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    TEXT_PROVIDER,
    TRANSLATION_MODEL_GEMINI,
    TRANSLATION_MODEL_GROQ,
    GROQ_BASE_URL,
)
from providers import LocalLLMProvider


class MetadataGenerator:
    """Generate metadata while keeping transcript content local by default."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.metadata_path: Optional[Path] = None
        self.thumbnail_prompts_path: Optional[Path] = None

    def generate(
        self,
        segments: list,
        original_title: str = "",
        use_gemini: bool = True,
    ) -> Dict:
        """
        Generate metadata for YouTube/Facebook.
        
        Args:
            segments: List of transcript segments
            original_title: Original video title (optional)
            use_gemini: Legacy cloud-provider preference when TEXT_PROVIDER is
                not ``local``.
            
        Returns:
            Dictionary with title, description, hashtags
        """
        if TEXT_PROVIDER == "local":
            try:
                return self._generate_with_local_llm(segments, original_title)
            except Exception as exc:
                if not ALLOW_CLOUD_FALLBACK:
                    print(f"[Metadata] Local LLM failed: {exc}; using defaults")
                    metadata = self._generate_default_metadata()
                    self._save_metadata(metadata)
                    self._save_thumbnail_prompts(metadata["thumbnail_prompt"])
                    return metadata
                print(f"[Metadata] Local LLM failed: {exc}; using cloud fallback")
                return self._generate_with_cloud(segments, original_title, use_gemini)

        return self._generate_with_cloud(segments, original_title, use_gemini)

    def _generate_with_cloud(
        self, segments: list, original_title: str, use_gemini: bool
    ) -> Dict:
        """Run legacy providers only when they are selected explicitly."""
        if TEXT_PROVIDER not in {"local", "gemini", "groq"}:
            raise ValueError("TEXT_PROVIDER must be 'local', 'gemini', or 'groq'")
        if TEXT_PROVIDER == "gemini":
            return self._generate_with_gemini(segments, original_title)
        if TEXT_PROVIDER == "groq":
            return self._generate_with_groq(segments, original_title)
        if use_gemini:
            try:
                return self._generate_with_gemini(segments, original_title)
            except Exception as e:
                print(f"[Metadata] Gemini failed: {e}, falling back to Groq")
                return self._generate_with_groq(segments, original_title)
        return self._generate_with_groq(segments, original_title)

    def _generate_with_local_llm(self, segments: list, original_title: str) -> Dict:
        client = LocalLLMProvider()
        response_text = client.generate(
            system_prompt=(
                "You are a Vietnamese social-media editor. Return only valid JSON "
                "matching the requested schema."
            ),
            user_prompt=self._metadata_prompt(segments, original_title),
            temperature=0.6,
            max_tokens=1024,
            json_mode=True,
        )
        return self._parse_and_save(response_text, segments)

    def _generate_with_gemini(
        self,
        segments: list,
        original_title: str,
    ) -> Dict:
        """Generate metadata using Gemini."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        try:
            import google.genai as genai
        except ImportError:
            raise ImportError(
                "Google GenAI not installed. Run: pip install google-genai"
            )

        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = self._metadata_prompt(segments, original_title)

        response = client.models.generate_content(
            model=TRANSLATION_MODEL_GEMINI,
            contents=prompt,
        )

        return self._parse_and_save(response.text, segments)

    def _generate_with_groq(
        self,
        segments: list,
        original_title: str,
    ) -> Dict:
        """Generate metadata using Groq LLaMA."""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured")

        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Groq SDK not installed. Run: pip install groq")

        client = Groq(api_key=GROQ_API_KEY)

        prompt = self._metadata_prompt(segments, original_title)

        response = client.chat.completions.create(
            model=TRANSLATION_MODEL_GROQ,
            messages=[
                {
                    "role": "system",
                    "content": "You are a social media expert. Generate engaging metadata.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        return self._parse_and_save(
            response.choices[0].message.content,
            segments,
        )

    def _prepare_summary(self, segments: list) -> str:
        """Prepare transcript as summary for prompt."""
        if not segments:
            return "No transcript available."

        # Take first few segments as summary
        summary_segments = segments[:10]
        lines = []
        for seg in summary_segments:
            text = seg.get("text_vi", seg.get("text", ""))
            lines.append(text)

        return " ".join(lines)

    def _metadata_prompt(self, segments: list, original_title: str) -> str:
        return f"""Based on the following video transcript, generate metadata for YouTube and Facebook.

Original title: {original_title or "N/A"}

Return ONLY valid JSON in this exact format:
{{
  "title": "Catchy Vietnamese YouTube title, max 100 chars",
  "description": "Vietnamese video description, max 5000 chars",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "thumbnail_prompt": "Description for an AI thumbnail generator"
}}

Transcript:
{self._prepare_summary(segments)}"""

    def _parse_and_save(self, response_text: str, segments: list) -> Dict:
        """Parse response and save metadata files."""
        try:
            # Extract JSON
            json_str = self._extract_json(response_text)
            metadata = json.loads(json_str)

        except (json.JSONDecodeError, TypeError, ValueError):
            print("[Metadata] Failed to parse response, using defaults")
            metadata = self._generate_default_metadata()

        metadata = self._normalize_metadata(metadata)

        # Save metadata JSON
        self._save_metadata(metadata)

        # Save thumbnail prompts
        self._save_thumbnail_prompts(metadata.get("thumbnail_prompt", ""))

        return metadata

    def _normalize_metadata(self, metadata: Dict) -> Dict:
        """Prevent malformed model output from reaching platform upload APIs."""
        defaults = self._generate_default_metadata()
        if not isinstance(metadata, dict):
            return defaults
        hashtags = metadata.get("hashtags", defaults["hashtags"])
        if not isinstance(hashtags, list):
            hashtags = defaults["hashtags"]
        return {
            "title": str(metadata.get("title") or defaults["title"])[:100],
            "description": str(metadata.get("description") or defaults["description"])[:5000],
            "hashtags": [str(tag).lstrip("#")[:100] for tag in hashtags[:15] if str(tag).strip()],
            "thumbnail_prompt": str(
                metadata.get("thumbnail_prompt") or defaults["thumbnail_prompt"]
            ),
        }

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            return text[start:end]
        return text.strip()

    def _generate_default_metadata(self) -> Dict:
        """Generate default metadata if AI fails."""
        return {
            "title": "Video đã được lồng tiếng Việt",
            "description": "Video đã được dịch và lồng tiếng Việt tự động bằng AI.",
            "hashtags": ["vietnamese", "dubbed", "translation", "ai"],
            "thumbnail_prompt": "Professional video thumbnail with Vietnamese text overlay",
        }

    def _save_metadata(self, metadata: Dict):
        """Save metadata to JSON file."""
        self.metadata_path = self.output_dir / "youtube_metadata.json"

        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"[Metadata] Saved to: {self.metadata_path}")

    def _save_thumbnail_prompts(self, prompt: str):
        """Save thumbnail prompts to text file."""
        self.thumbnail_prompts_path = self.output_dir / "thumbnail_prompts.txt"

        with open(self.thumbnail_prompts_path, "w", encoding="utf-8") as f:
            f.write("Thumbnail Generation Prompts\n")
            f.write("=" * 40 + "\n\n")
            f.write(f"Primary Prompt:\n{prompt}\n\n")
            f.write("Alternative styles:\n")
            f.write("1. Modern minimalist with bold text\n")
            f.write("2. Vibrant colors with overlay graphics\n")
            f.write("3. Professional news style\n")

        print(f"[Metadata] Saved thumbnail prompts to: {self.thumbnail_prompts_path}")

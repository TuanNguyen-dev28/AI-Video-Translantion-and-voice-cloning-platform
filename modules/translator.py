"""Translate transcript segments with a local LLM by default."""
import json
from pathlib import Path
from typing import List, Dict, Optional

from config import (
    ALLOW_CLOUD_FALLBACK,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    TEXT_PROVIDER,
    TRANSLATION_BATCH_SIZE,
    TRANSLATION_MODEL_GEMINI,
    TRANSLATION_MODEL_GROQ,
)
from providers import LocalLLMProvider


class Translator:
    """Translate timestamped segments while retaining their IDs and timing."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.translated_segments: List[Dict] = []
        self.transcript_vi_path: Optional[Path] = None

    def translate(self, segments: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Translate segments to Vietnamese.

        Args:
            segments: List of transcript segments with text
            use_gemini: Legacy cloud-provider preference when TEXT_PROVIDER is
                not ``local``.

        Returns:
            List of segments with added "text_vi" field
        """
        if not segments:
            return []

        if TEXT_PROVIDER == "local":
            try:
                return self._translate_with_local_llm(segments)
            except Exception as exc:
                if not ALLOW_CLOUD_FALLBACK:
                    raise RuntimeError(
                        "Local translation failed. Start the configured local LLM or "
                        "set ALLOW_CLOUD_FALLBACK=true to intentionally use cloud AI."
                    ) from exc
                print(f"[Translator] Local LLM failed: {exc}; using cloud fallback")
                return self._translate_with_cloud(segments, use_gemini)

        return self._translate_with_cloud(segments, use_gemini)

    def _translate_with_cloud(
        self, segments: List[Dict], use_gemini: bool
    ) -> List[Dict]:
        """Run the original cloud providers when explicitly selected."""
        if TEXT_PROVIDER not in {"gemini", "groq", "local"}:
            raise ValueError("TEXT_PROVIDER must be 'local', 'gemini', or 'groq'")
        if TEXT_PROVIDER == "gemini":
            return self._translate_with_gemini(segments)
        if TEXT_PROVIDER == "groq":
            return self._translate_with_groq(segments)
        if use_gemini:
            try:
                return self._translate_with_gemini(segments)
            except Exception as e:
                print(f"[Translator] Gemini failed: {e}, falling back to Groq")
                return self._translate_with_groq(segments)
        return self._translate_with_groq(segments)

    def _translate_with_local_llm(self, segments: List[Dict]) -> List[Dict]:
        """Translate in bounded batches to avoid exceeding local model context."""
        client = LocalLLMProvider()
        translations: List[Dict] = []
        for start in range(0, len(segments), TRANSLATION_BATCH_SIZE):
            batch = segments[start : start + TRANSLATION_BATCH_SIZE]
            response_text = client.generate(
                system_prompt=(
                    "You are a professional translator. Translate accurately to "
                    "natural Vietnamese and return only the requested JSON."
                ),
                user_prompt=self._translation_prompt(batch),
                temperature=0.2,
                max_tokens=4096,
                json_mode=True,
            )
            translations.extend(self._parse_translation_response(response_text, batch))

        self.translated_segments = self._merge_translations(segments, translations)
        self._save_translated_json()
        return self.translated_segments

    def _translate_with_gemini(self, segments: List[Dict]) -> List[Dict]:
        """Translate using Gemini 2.0 Flash."""
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        try:
            import google.genai as genai
        except ImportError:
            raise ImportError(
                "Google GenAI not installed. Run: pip install google-genai"
            )

        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = self._translation_prompt(segments)

        response = client.models.generate_content(
            model=TRANSLATION_MODEL_GEMINI,
            contents=prompt,
        )

        translations = self._parse_translation_response(response.text, segments)
        self.translated_segments = self._merge_translations(segments, translations)
        self._save_translated_json()

        return self.translated_segments

    def _translate_with_groq(self, segments: List[Dict]) -> List[Dict]:
        """Translate using Groq LLaMA 3.3 70B."""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not configured")

        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Groq SDK not installed. Run: pip install groq")

        client = Groq(api_key=GROQ_API_KEY)
        prompt = self._translation_prompt(segments)

        response = client.chat.completions.create(
            model=TRANSLATION_MODEL_GROQ,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate accurately to Vietnamese.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        translations = self._parse_translation_response(
            response.choices[0].message.content,
            segments,
        )

        self.translated_segments = self._merge_translations(segments, translations)
        self._save_translated_json()

        return self.translated_segments

    def _prepare_text(self, segments: List[Dict]) -> str:
        """Prepare segments as text for translation prompt."""
        lines = []
        for seg in segments:
            seg_id = seg.get("id", "")
            text = seg.get("text", "")
            lines.append(f"[{seg_id}] {text}")
        return "\n".join(lines)

    def _translation_prompt(self, segments: List[Dict]) -> str:
        return f"""Translate the following transcript to Vietnamese.
Keep the same segment IDs and numbering. Return ONLY valid JSON exactly in this format:
{{"translations": [{{"id": 0, "text_vi": "translated text"}}, ...]}}

Rules:
- Include one item for every input ID.
- Keep names, brand names, and technical terms in their original language when appropriate.
- Use natural spoken Vietnamese and keep each translation concise enough to match timing.

Transcript to translate:
{self._prepare_text(segments)}"""

    def _parse_translation_response(
        self, response_text: str, segments: List[Dict]
    ) -> List[Dict]:
        """Parse translation response from AI."""
        try:
            json_str = self._extract_json(response_text)
            data = json.loads(json_str)
            return data.get("translations", [])
        except (json.JSONDecodeError, TypeError, KeyError):
            print("[Translator] Failed to parse response, using original text")
            return [{"id": seg["id"], "text_vi": seg.get("text", "")} for seg in segments]

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

    def _merge_translations(
        self, segments: List[Dict], translations: List[Dict]
    ) -> List[Dict]:
        """Merge translations into original segments."""
        translation_map = {}
        for translation in translations:
            try:
                translation_map[int(translation["id"])] = str(translation["text_vi"])
            except (KeyError, TypeError, ValueError):
                continue
        result = []
        for seg in segments:
            new_seg = seg.copy()
            new_seg["text_vi"] = translation_map.get(seg["id"], seg.get("text", ""))
            result.append(new_seg)
        return result

    def _save_translated_json(self):
        """Save translated transcript to JSON."""
        self.transcript_vi_path = self.output_dir / "transcript_vi.json"
        output = {
            "segments": self.translated_segments,
            "total_segments": len(self.translated_segments),
            "language": "vi",
        }
        with open(self.transcript_vi_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[Translator] Saved to: {self.transcript_vi_path}")

    def get_segment_count(self) -> int:
        """Get total number of segments."""
        return len(self.translated_segments)

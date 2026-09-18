"""Run a small live check against the configured self-hosted LLM."""

from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import ensure_data_dir
from modules.metadata_generator import MetadataGenerator
from modules.translator import Translator
from providers import LocalLLMProvider


def main() -> None:
    provider = LocalLLMProvider()
    provider.ensure_ready()

    segments = [{"id": 0, "text": "Welcome to our video."}]
    translation_response = provider.generate(
        system_prompt="You are a translator. Return only valid JSON.",
        user_prompt=(
            "Translate to Vietnamese. Return only JSON: "
            '{"translations":[{"id":0,"text_vi":"..."}]}\n'
            "[0] Welcome to our video."
        ),
        temperature=0,
        max_tokens=128,
        json_mode=True,
    )
    output_dir = ensure_data_dir() / "verification"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Translation response: {translation_response}")
    translations = Translator(output_dir)._parse_translation_response(
        translation_response, segments
    )
    if not translations or not translations[0].get("text_vi"):
        raise RuntimeError("Local LLM did not return a usable translation")

    metadata_response = provider.generate(
        system_prompt="You are a Vietnamese social-media editor. Return only valid JSON.",
        user_prompt=(
            "Return only JSON: "
            '{"title":"...","description":"...","hashtags":["..."],'
            '"thumbnail_prompt":"..."}. '
            "Topic: welcome video about local AI."
        ),
        temperature=0,
        max_tokens=256,
        json_mode=True,
    )
    print(f"Metadata response: {metadata_response}")
    metadata = MetadataGenerator(output_dir)._parse_and_save(metadata_response, segments)
    if not metadata["title"] or not metadata["hashtags"]:
        raise RuntimeError("Local LLM did not return usable metadata")

    print(
        "Local LLM is ready. "
        f"Translation: {translations[0]['text_vi']} | Title: {metadata['title']}"
    )


if __name__ == "__main__":
    main()

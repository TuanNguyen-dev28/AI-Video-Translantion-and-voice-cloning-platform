"""Regression tests for local-provider parsing and durable job state."""

from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

from config import ensure_data_dir
from main import JobStore
from modules.metadata_generator import MetadataGenerator
from modules.tts_generator import TTSGenerator
from modules.translator import Translator
from providers.local_llm import LocalLLMProvider


class LocalFirstTests(unittest.TestCase):
    @staticmethod
    def _runtime_dir(name: str) -> Path:
        directory = ensure_data_dir() / "test-artifacts" / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def test_translation_parses_string_ids_and_preserves_segments(self):
        segments = [{"id": 0, "text": "Hello"}, {"id": 1, "text": "World"}]
        translator = Translator(self._runtime_dir("translation"))
        translations = translator._parse_translation_response(
            '{"translations": ['
            '{"id": "0", "text_vi": "Xin chao"}, '
            '{"id": "1", "text_vi": "The gioi"}'
            ']}',
            segments,
        )
        merged = translator._merge_translations(segments, translations)

        self.assertEqual([item["text_vi"] for item in merged], ["Xin chao", "The gioi"])

    def test_metadata_is_normalized_before_it_is_saved(self):
        output_dir = self._runtime_dir("metadata")
        metadata = MetadataGenerator(output_dir)._parse_and_save(
            '{"title": "Tieu de", "description": "Mo ta", '
            '"hashtags": ["#ai", 42], "thumbnail_prompt": "Prompt"}',
            [],
        )

        self.assertEqual(metadata["hashtags"], ["ai", "42"])
        self.assertTrue((output_dir / "youtube_metadata.json").exists())
        self.assertTrue((output_dir / "thumbnail_prompts.txt").exists())

    def test_job_store_persists_a_completed_job_and_messages(self):
        store = JobStore(self._runtime_dir("jobs") / "jobs.sqlite3")
        job_id = str(uuid.uuid4())
        store.create_job(job_id, {"url": "https://example.com/video"})
        store.add_message(job_id, "STEP 1", "Started")
        store.set_result(job_id, {"success": True, "output_dir": "output/test"})

        job = store.get_job(job_id)
        messages = store.get_messages(job_id)

        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(messages, ["**STEP 1**: Started"])

    def test_local_llm_client_keeps_configuration_local(self):
        provider = LocalLLMProvider(
            base_url="http://127.0.0.1:11434/v1/",
            model="test-model",
        )
        self.assertEqual(provider.base_url, "http://127.0.0.1:11434/v1")
        self.assertEqual(provider.model, "test-model")

    def test_local_tts_fails_loudly_when_not_configured(self):
        generator = TTSGenerator(self._runtime_dir("tts"))
        with (
            patch("modules.tts_generator.TTS_PROVIDER", "local"),
            patch("modules.tts_generator.ALLOW_CLOUD_FALLBACK", False),
            self.assertRaisesRegex(RuntimeError, "Local TTS did not generate audio"),
        ):
            generator._generate_segment(0, "Xin chao", 1.0, "default")


if __name__ == "__main__":
    unittest.main()

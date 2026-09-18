"""
Pipeline Orchestrator - Main pipeline execution.
Coordinates all steps from download to upload.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Literal, Optional, Callable

from config import AUTO_PUBLISH, TEXT_PROVIDER, TTS_PROVIDER, ensure_output_dir, TEMPO_SLOWDOWN
from modules import (
    VideoDownloader,
    AudioProcessor,
    ASRTranscriber,
    Translator,
    TTSGenerator,
    AudioMixer,
    VideoComposer,
    MetadataGenerator,
    Uploader,
)
from providers import LocalLLMProvider, LocalTTSProvider


class Pipeline:
    """
    Main pipeline orchestrator for video translation.
    Executes all 9 steps in sequence.
    """

    def __init__(
        self,
        output_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.output_callback = output_callback
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = ensure_output_dir(self.timestamp)

        # Module instances
        self.downloader: Optional[VideoDownloader] = None
        self.audio_processor: Optional[AudioProcessor] = None
        self.asr: Optional[ASRTranscriber] = None
        self.translator: Optional[Translator] = None
        self.tts: Optional[TTSGenerator] = None
        self.mixer: Optional[AudioMixer] = None
        self.composer: Optional[VideoComposer] = None
        self.metadata_gen: Optional[MetadataGenerator] = None
        self.uploader: Optional[Uploader] = None

        # Results
        self.video_path: Optional[Path] = None
        self.audio_path: Optional[Path] = None
        self.no_vocals_path: Optional[Path] = None
        self.segments: List[Dict] = []
        self.segment_paths: List[Path] = []
        self.final_audio_path: Optional[Path] = None
        self.dubbed_video_path: Optional[Path] = None
        self.metadata: Dict = {}
        self.upload_results: Dict = {}

    def _log(self, step: str, message: str):
        """Log progress with callback."""
        print(f"[{step}] {message}")
        if self.output_callback:
            self.output_callback(step, message)

    def run(
        self,
        url: str = "",
        voice_id: str = "default",
        background_music: Literal["duck", "none"] = "none",
        target_platforms: Optional[List[Literal["youtube", "facebook"]]] = None,
        local_video_path: Optional[str] = None,
    ) -> Dict:
        """
        Execute the full pipeline.

        Args:
            url: Video URL (YouTube/TikTok/Douyin) - required if no local file
            voice_id: TTS voice ID
            background_music: "duck" or "none"
            target_platforms: Platforms to upload to, after owner approval
            local_video_path: Path to a local video file (skips download if provided)

        Returns:
            Dictionary with results and URLs
        """
        try:
            # Initialize modules
            self.downloader = VideoDownloader(self.output_dir)
            self.audio_processor = AudioProcessor(self.output_dir)
            self.asr = ASRTranscriber(self.output_dir)
            self.translator = Translator(self.output_dir)
            self.tts = TTSGenerator(self.output_dir)
            self.mixer = AudioMixer(self.output_dir)
            self.composer = VideoComposer(self.output_dir)
            self.metadata_gen = MetadataGenerator(self.output_dir)
            self.uploader = Uploader(self.output_dir)

            # Fail before expensive download/transcription when a required local
            # runtime is missing or configured for a different model.
            if TEXT_PROVIDER == "local":
                self._log("PRECHECK", "Checking local LLM runtime...")
                LocalLLMProvider().ensure_ready()
                self._log("PRECHECK", "Local LLM is ready")
            if TTS_PROVIDER == "local":
                LocalTTSProvider()  # validates required local TTS configuration
                self._log("PRECHECK", "Local TTS configuration is present")

            # STEP 1: Download video or use local file
            if local_video_path:
                self._log("STEP 1", "Using local video file...")
                self.video_path = self.downloader.use_local_file(local_video_path, self.timestamp)
                self._log("STEP 1", f"Local video loaded: {self.video_path.name}")
            else:
                if not url:
                    raise ValueError("Either video URL or local file must be provided")
                self._log("STEP 1", "Downloading video...")
                self.video_path = self.downloader.download(url, self.timestamp)
                self._log("STEP 1", f"Video downloaded: {self.video_path.name}")

            if not self.video_path or not self.video_path.exists():
                raise RuntimeError(f"Video file not found after step 1: {self.video_path}")

            # STEP 2: Extract audio
            self._log("STEP 2", "Extracting audio...")
            self.audio_path = self.audio_processor.extract_audio(self.video_path)
            self._log("STEP 2", f"Audio extracted: {self.audio_path.name}")

            if not self.audio_path or not self.audio_path.exists():
                raise RuntimeError(f"Audio file not found after step 2: {self.audio_path}")

            # STEP 2.5: Process background music
            if background_music == "duck":
                self._log("STEP 2.5", "Processing background music (duck)...")
                self.no_vocals_path = self.audio_processor.process_background_music(
                    self.audio_path,
                    background_music,
                )
                if self.no_vocals_path and self.no_vocals_path.exists():
                    self._log("STEP 2.5", f"Background music processed: {self.no_vocals_path.name}")
                else:
                    self._log("STEP 2.5", "Background music processing skipped (demucs not available)")
                    self.no_vocals_path = None
            else:
                self._log("STEP 2.5", "Background music: none (skipped)")
                self.no_vocals_path = None

            # STEP 3: ASR transcription
            self._log("STEP 3", "Transcribing audio...")
            self.asr.transcribe(self.audio_path)
            self.segments = self.asr.segments
            self._log("STEP 3", f"Transcribed {len(self.segments)} segments")

            if not self.segments:
                raise RuntimeError("No segments transcribed from audio")

            self.asr.release_resources()
            self._log("STEP 3", "Released ASR GPU resources")

            # STEP 4: Translate to Vietnamese
            self._log("STEP 4", "Translating to Vietnamese...")
            self.segments = self.translator.translate(self.segments)
            self._log("STEP 4", f"Translation complete: {len(self.segments)} segments")

            # Verify all segments have text_vi
            for seg in self.segments:
                if "text_vi" not in seg or not seg["text_vi"]:
                    seg["text_vi"] = seg.get("text", "")

            # STEP 5: TTS generation
            self._log("STEP 5", "Generating Vietnamese voice...")
            self.segment_paths = self.tts.generate(self.segments, voice_id)
            self._log("STEP 5", f"Generated {len(self.segment_paths)} TTS segments")

            if not self.segment_paths:
                raise RuntimeError("No TTS segments generated")

            # Verify TTS files exist
            missing = [str(p) for p in self.segment_paths if not p.exists()]
            if missing:
                self._log("STEP 5", f"WARNING: {len(missing)} TTS files missing")

            # STEP 6: Mix audio
            self._log("STEP 6", "Mixing audio...")
            needs_slowdown = self._check_slowdown_needed()

            self.final_audio_path = self.mixer.mix(
                self.segments,
                self.segment_paths,
                self.no_vocals_path,
                needs_slowdown,
            )
            self._log("STEP 6", f"Audio mixed: {self.final_audio_path.name}")

            if not self.final_audio_path or not self.final_audio_path.exists():
                raise RuntimeError(f"Mixed audio file not found: {self.final_audio_path}")

            # STEP 7: Compose video
            self._log("STEP 7", "Composing dubbed video...")
            self.dubbed_video_path = self.composer.compose(
                self.video_path,
                self.final_audio_path,
            )
            self._log("STEP 7", f"Video composed: {self.dubbed_video_path.name}")

            if not self.dubbed_video_path or not self.dubbed_video_path.exists():
                raise RuntimeError(f"Dubbed video file not found: {self.dubbed_video_path}")

            # STEP 8: Generate metadata
            self._log("STEP 8", "Generating metadata...")
            self.metadata = self.metadata_gen.generate(self.segments)
            self._log("STEP 8", f"Metadata generated: {self.metadata.get('title', 'N/A')}")

            # STEP 9: Upload
            target_platforms = target_platforms or []
            if target_platforms and AUTO_PUBLISH:
                self._log("STEP 9", f"Uploading to {', '.join(target_platforms)}...")
                self.upload_results = self.uploader.upload_all(
                    self.dubbed_video_path,
                    self.metadata,
                    target_platforms,
                )
            elif target_platforms:
                self._log(
                    "STEP 9",
                    "Upload approval required; video kept locally. Set AUTO_PUBLISH=true "
                    "only after review to publish automatically.",
                )
            else:
                self._log("STEP 9", "No upload requested (no target platforms)")

            # Complete
            self._log("DONE", "PIPELINE COMPLETE")

            return {
                "success": True,
                "youtube_url": self.upload_results.get("youtube", ""),
                "facebook_url": self.upload_results.get("facebook", ""),
                "output_dir": str(self.output_dir),
                "dubbed_video": str(self.dubbed_video_path),
                "metadata": self.metadata,
                "upload_pending": bool(target_platforms) and not AUTO_PUBLISH,
            }

        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            self._log("ERROR", error_msg)
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg,
                "output_dir": str(self.output_dir),
            }

    def _check_slowdown_needed(self) -> bool:
        """Check if audio needs slowdown based on timing."""
        if not self.segments or not self.segment_paths:
            return False
            
        try:
            # Get original total duration from segments
            original_duration = sum(seg.get('end', 0) - seg.get('start', 0) for seg in self.segments)
            
            # Get TTS total duration
            tts_duration = 0.0
            import wave
            for path in self.segment_paths:
                if not path.exists():
                    continue
                try:
                    with wave.open(str(path), "rb") as w:
                        frames = w.getnframes()
                        rate = w.getframerate()
                        if rate > 0:
                            tts_duration += frames / float(rate)
                except Exception:
                    pass
                    
            if tts_duration > original_duration * 1.1: # 10% tolerance
                self._log("STEP 6", f"TTS ({tts_duration:.1f}s) is significantly longer than original ({original_duration:.1f}s). Applying slowdown.")
                return True
        except Exception as e:
            self._log("WARNING", f"Error checking audio duration: {e}")
            
        return False

    def get_progress(self) -> Dict[str, str]:
        """Get current progress state."""
        return {
            "timestamp": self.timestamp,
            "output_dir": str(self.output_dir),
        }

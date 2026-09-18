"""
Video Downloader Module - Supports YouTube, TikTok, Douyin, and local files.
"""
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Literal, Union
from urllib.parse import urlparse

from config import (
    OUTPUT_DIR,
    PLATFORM_PATTERNS,
    VIDEO_FORMAT,
    COOKIES_FILE,
    ensure_output_dir,
)


class VideoDownloader:
    """Handles video downloading from various platforms."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.video_path: Optional[Path] = None

    def detect_platform(self, url: str) -> Literal["youtube", "tiktok", "douyin", "unknown"]:
        """Detect video platform from URL."""
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace("www.", "").replace("m.", "")

        for platform, patterns in PLATFORM_PATTERNS.items():
            if any(pattern in domain for pattern in patterns):
                return platform
        return "unknown"

    def download(self, url: str, timestamp: str) -> Path:
        """Download video from URL based on platform."""
        platform = self.detect_platform(url)

        if platform == "unknown":
            raise ValueError(f"Unsupported platform: {url}")

        output_path = ensure_output_dir(timestamp)

        if platform == "youtube":
            return self._download_youtube(url, output_path, timestamp)
        elif platform == "tiktok":
            return self._download_tiktok(url, output_path, timestamp)
        elif platform == "douyin":
            return self._download_douyin(url, output_path, timestamp)
        else:
            raise ValueError(f"Platform {platform} not supported yet")

    def use_local_file(self, file_path: Union[str, Path], timestamp: str) -> Path:
        """
        Use a locally uploaded video file as the video source.
        Copies the file to the output directory with a proper naming convention.

        Args:
            file_path: Path to the local video file
            timestamp: Timestamp string for naming

        Returns:
            Path to the video file in the output directory
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Local video file not found: {file_path}")

        output_path = ensure_output_dir(timestamp)
        output_filename = f"{timestamp}_local{file_path.suffix}"
        output_file = output_path / output_filename
        shutil.copy2(file_path, output_file)
        self.video_path = output_file
        return output_file

    def _download_youtube(self, url: str, output_path: Path, timestamp: str) -> Path:
        """Download from YouTube using yt-dlp with multiple fallback strategies."""
        import sys
        output_template = str(output_path / f"{timestamp}_%(id)s.%(ext)s")

        base_args = [
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--no-check-certificates",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "--add-header", "Accept-Language: en-US,en;q=0.9",
            "--sleep-interval", "1",
            "--max-sleep-interval", "5",
            "-o", output_template,
        ]

        strategies = []

        if COOKIES_FILE:
            strategies.append({
                "name": "cookies_file",
                "args": ["--cookies", COOKIES_FILE],
                "extractor_args": "youtube:player_client=web,android,ios;player_skip=webpage",
            })

        strategies.extend([
            {
                "name": "browser_cookies",
                "args": ["--cookies-from-browser", "chrome"],
                "extractor_args": "youtube:player_client=web,android,ios;player_skip=webpage",
            },
            {
                "name": "alt_client_ios",
                "args": [],
                "extractor_args": "youtube:player_client=ios;player_skip=webpage",
            },
            {
                "name": "alt_client_android",
                "args": [],
                "extractor_args": "youtube:player_client=android;player_skip=webpage",
            },
            {
                "name": "alt_client_web_creator",
                "args": [],
                "extractor_args": "youtube:player_client=web_creator;player_skip=webpage",
            },
        ])

        last_error = None
        last_stdout = ""

        for strategy in strategies:
            cmd = [sys.executable, "-m", "yt_dlp"] + base_args + strategy["args"] + [
                "--extractor-args", strategy["extractor_args"],
                url,
            ]

            print(f"[Downloader] Trying strategy: {strategy['name']}")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                print(f"[Downloader] YouTube ({strategy['name']}): {result.stdout}")

                for f in output_path.glob(f"{timestamp}_*.mp4"):
                    self.video_path = f
                    return f

                raise FileNotFoundError("Downloaded video not found")

            except subprocess.CalledProcessError as e:
                last_error = e
                last_stdout = getattr(e, "stdout", "") or ""
                print(f"[Downloader] Strategy '{strategy['name']}' failed: {(e.stderr or '')[:200]}")
                time.sleep(1)

        stderr = (getattr(last_error, "stderr", "") or "").strip() if last_error else ""
        stdout = (last_stdout or "").strip()
        raise RuntimeError(
            f"YouTube download failed after all strategies: {stderr or last_error} | stdout={stdout}"
        )

    def _download_tiktok(self, url: str, output_path: Path, timestamp: str) -> Path:
        """Download from TikTok using yt-dlp."""
        import sys
        output_template = str(output_path / f"{timestamp}_tiktok.%(ext)s")

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "best[ext=mp4]/best",
            "--no-playlist",
            "-o", output_template,
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"[Downloader] TikTok: {result.stdout}")

            for f in output_path.glob(f"{timestamp}_tiktok.*"):
                if f.suffix == ".mp4":
                    self.video_path = f
                    return f

            for f in output_path.glob("*.mp4"):
                self.video_path = f
                return f

            raise FileNotFoundError("Downloaded video not found")

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"TikTok download failed: {e.stderr}")

    def _download_douyin(self, url: str, output_path: Path, timestamp: str) -> Path:
        """Download from Douyin using Playwright."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        video_path = output_path / f"{timestamp}_douyin.mp4"

        def download_with_playwright():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                try:
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_selector("video", timeout=30000)

                    video_url = page.eval_on_selector(
                        "video", "el => el.src || el.querySelector('source')?.src"
                    )

                    if not video_url:
                        raise ValueError("Could not extract video URL")

                    subprocess.run(
                        [
                            "curl",
                            "-L",
                            "-o",
                            str(video_path),
                            video_url,
                        ],
                        check=True,
                    )

                finally:
                    browser.close()

        try:
            download_with_playwright()
            self.video_path = video_path
            return video_path
        except Exception as e:
            raise RuntimeError(f"Douyin download failed: {e}")

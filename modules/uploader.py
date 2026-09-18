"""
Uploader Module - Upload video to YouTube and Facebook.
Handles Step 9: Upload dubbed video to social platforms.
"""
import json
from pathlib import Path
from typing import Dict, Optional, Literal

from config import (
    CLIENT_SECRETS_FILE,
    FB_PAGE_ACCESS_TOKEN,
)


class Uploader:
    """Handles video upload to YouTube and Facebook."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.youtube_video_id: Optional[str] = None
        self.youtube_url: Optional[str] = None
        self.facebook_url: Optional[str] = None

    def upload_all(
        self,
        video_path: Path,
        metadata: Dict,
        platforms: list,
    ) -> Dict[Literal["youtube", "facebook"], str]:
        """
        Upload video to specified platforms.
        
        Args:
            video_path: Path to dubbed video
            metadata: Video metadata (title, description, hashtags)
            platforms: List of platforms to upload to
            
        Returns:
            Dictionary mapping platform to video URL
        """
        results = {}

        for platform in platforms:
            if platform == "youtube":
                try:
                    url = self.upload_youtube(video_path, metadata)
                    results["youtube"] = url
                except Exception as e:
                    print(f"[Uploader] YouTube upload failed: {e}")
                    results["youtube"] = ""

            elif platform == "facebook":
                try:
                    url = self.upload_facebook(video_path, metadata)
                    results["facebook"] = url
                except Exception as e:
                    print(f"[Uploader] Facebook upload failed: {e}")
                    results["facebook"] = ""

        return results

    def upload_youtube(
        self,
        video_path: Path,
        metadata: Dict,
    ) -> str:
        """
        Upload video to YouTube using OAuth2.
        
        Args:
            video_path: Path to video file
            metadata: Video metadata
            
        Returns:
            YouTube video URL
        """
        if not CLIENT_SECRETS_FILE.exists():
            raise FileNotFoundError(
                f"Client secrets file not found: {CLIENT_SECRETS_FILE}. "
                "Download from Google Cloud Console."
            )

        try:
            import google.oauth2.credentials
            import google_auth_oauthlib.flow
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            raise ImportError(
                "Google API libraries not installed. "
                "Run: pip install google-auth google-auth-oauthlib google-api-python-client"
            )

        # Build title and description
        title = metadata.get("title", "Untitled Video")[:100]
        hashtags = metadata.get("hashtags", [])
        description = metadata.get("description", "")
        if hashtags:
            hashtags_str = " ".join(["#" + tag for tag in hashtags])
            description = f"{description}\n\n{hashtags_str}"

        # Initialize OAuth flow
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )

        # Get credentials
        credentials = flow.run_local_server(port=0)

        # Build YouTube API client
        youtube = build("youtube", "v3", credentials=credentials)

        # Create upload request
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": hashtags,
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            },
            media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
        )

        # Execute upload
        response = request.execute()

        self.youtube_video_id = response["id"]
        self.youtube_url = f"https://www.youtube.com/watch?v={self.youtube_video_id}"

        print(f"[Uploader] Uploaded to YouTube: {self.youtube_url}")
        return self.youtube_url

    def upload_facebook(
        self,
        video_path: Path,
        metadata: Dict,
    ) -> str:
        """
        Upload video to Facebook Page using Graph API.
        
        Args:
            video_path: Path to video file
            metadata: Video metadata
            
        Returns:
            Facebook video URL
        """
        if not FB_PAGE_ACCESS_TOKEN:
            raise ValueError("FB_PAGE_ACCESS_TOKEN not configured")

        try:
            import httpx
        except ImportError:
            raise ImportError("httpx not installed. Run: pip install httpx")

        title = metadata.get("title", "Untitled Video")[:100]
        description = metadata.get("description", "")[:500]

        # Step 1: Get page ID
        page_info = self._get_facebook_page_info()

        # Step 2: Upload video
        video_url = self._upload_facebook_video(
            page_id=page_info["id"],
            video_path=video_path,
            title=title,
            description=description,
        )

        self.facebook_url = video_url
        print(f"[Uploader] Uploaded to Facebook: {self.facebook_url}")
        return self.facebook_url

    def _get_facebook_page_info(self) -> Dict:
        """Get Facebook Page information."""
        import httpx

        with httpx.Client() as client:
            response = client.get(
                "https://graph.facebook.com/v18.0/me",
                params={
                    "fields": "id,name",
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                },
            )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to get page info: {response.text}")

        return response.json()

    def _upload_facebook_video(
        self,
        page_id: str,
        video_path: Path,
        title: str,
        description: str,
    ) -> str:
        """
        Upload video to Facebook using Graph API.
        Uses the chunked upload method for larger files.
        """
        import httpx

        endpoint = f"https://graph.facebook.com/v18.0/{page_id}/videos"

        # Prepare metadata
        data = {
            "title": title,
            "description": description,
            "access_token": FB_PAGE_ACCESS_TOKEN,
        }

        # Read video file
        with open(video_path, "rb") as f:
            video_data = f.read()

        # Upload video
        with httpx.Client(timeout=300.0) as client:
            files = {"source": (video_path.name, video_data, "video/mp4")}

            response = client.post(
                endpoint,
                data=data,
                files=files,
            )

        if response.status_code != 200:
            raise RuntimeError(f"Facebook upload failed: {response.text}")

        result = response.json()
        video_id = result.get("id")

        return f"https://www.facebook.com/{page_id}/videos/{video_id}"

    def get_youtube_url(self) -> Optional[str]:
        """Get last YouTube upload URL."""
        return self.youtube_url

    def get_facebook_url(self) -> Optional[str]:
        """Get last Facebook upload URL."""
        return self.facebook_url

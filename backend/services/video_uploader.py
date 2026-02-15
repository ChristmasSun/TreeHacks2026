"""
Video Uploader Service
Uploads Manim explainer videos to Render for public access.
"""
import os
import logging
from pathlib import Path
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Render service URL
RENDER_SERVICE_URL = os.getenv("RTMS_SERVICE_URL", "https://rtms-webhook.onrender.com")

# Cache of uploaded videos: local_path -> public_url
_uploaded_videos: dict[str, str] = {}


async def upload_video_to_render(video_path: str) -> Optional[str]:
    """
    Upload a video file to Render and return the public URL.

    Args:
        video_path: Local path to the video file

    Returns:
        Public URL of the uploaded video, or None if upload failed
    """
    # Check cache first
    if video_path in _uploaded_videos:
        logger.info(f"Video already uploaded: {_uploaded_videos[video_path]}")
        return _uploaded_videos[video_path]

    path = Path(video_path)
    if not path.exists():
        logger.error(f"Video file not found: {video_path}")
        return None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(path, "rb") as f:
                files = {"video": (path.name, f, "video/mp4")}
                response = await client.post(
                    f"{RENDER_SERVICE_URL}/api/videos/upload",
                    files=files
                )

            if response.is_success:
                data = response.json()
                public_url = data.get("url")
                if public_url:
                    _uploaded_videos[video_path] = public_url
                    logger.info(f"Uploaded video: {path.name} -> {public_url}")
                    return public_url
            else:
                logger.error(f"Failed to upload video: {response.status_code} - {response.text}")

    except Exception as e:
        logger.error(f"Error uploading video to Render: {e}")

    return None


async def upload_quiz_videos(concepts: list[dict]) -> list[dict]:
    """
    Upload all videos for quiz concepts and update with public URLs.

    Args:
        concepts: List of concept dicts with video_path

    Returns:
        Updated concepts with public_video_url added
    """
    for concept in concepts:
        video_path = concept.get("video_path")
        if video_path:
            public_url = await upload_video_to_render(video_path)
            if public_url:
                concept["public_video_url"] = public_url
                logger.info(f"Concept '{concept.get('concept')}' video: {public_url}")

    return concepts


def get_cached_video_url(video_path: str) -> Optional[str]:
    """Get the cached public URL for a video path."""
    return _uploaded_videos.get(video_path)


def clear_video_cache():
    """Clear the video URL cache."""
    _uploaded_videos.clear()

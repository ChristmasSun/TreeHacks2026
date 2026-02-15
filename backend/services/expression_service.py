"""
Expression Analysis Service

Handles video frames from RTMS (via Render WebSocket) and forwards them
to the local expression-dashboard for facial emotion analysis.
"""
import os
import base64
import logging
import httpx

from .render_ws_client import register_handler

logger = logging.getLogger(__name__)

# Local expression-dashboard URL
EXPRESSION_SERVICE_URL = os.getenv("EXPRESSION_SERVICE_URL", "http://localhost:8001")

# HTTP client for forwarding frames
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create the HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def handle_video_frame(message: dict):
    """
    Handle video frame from RTMS via Render WebSocket.
    Forward the frame to the local expression-dashboard.
    """
    data = message.get("data", {})
    meeting_id = data.get("meetingId")
    frame_b64 = data.get("frame")
    timestamp = data.get("timestamp")

    if not frame_b64 or not meeting_id:
        logger.warning("[Expression] Received video_frame without frame or meetingId")
        return

    # Decode base64 frame
    try:
        frame_bytes = base64.b64decode(frame_b64)
    except Exception as e:
        logger.error(f"[Expression] Failed to decode frame: {e}")
        return

    logger.info(f"[Expression] Received frame for meeting {meeting_id} ({len(frame_bytes)} bytes)")

    # Forward to local expression-dashboard
    try:
        client = get_http_client()
        files = {"frame": ("frame.jpg", frame_bytes, "image/jpeg")}
        form_data = {"meeting_id": meeting_id, "timestamp": str(timestamp or 0)}

        response = await client.post(
            f"{EXPRESSION_SERVICE_URL}/api/frames",
            files=files,
            data=form_data,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "ok":
                emotions = result.get("emotions", {})
                dominant = max(emotions, key=emotions.get) if emotions else "unknown"
                logger.info(
                    f"[Expression] Analysis: {result.get('faces', 0)} faces, "
                    f"dominant={dominant} ({emotions.get(dominant, 0):.1%})"
                )
            elif result.get("status") == "throttled":
                logger.debug("[Expression] Frame throttled by expression service")
            elif result.get("status") == "no_faces":
                logger.debug("[Expression] No faces detected in frame")
        else:
            logger.warning(f"[Expression] Service returned {response.status_code}")

    except httpx.ConnectError:
        # Expression service not running - don't spam logs
        pass
    except Exception as e:
        logger.error(f"[Expression] Error forwarding frame: {e}")


def init_expression_service():
    """Initialize the expression service by registering the video_frame handler."""
    register_handler("video_frame", handle_video_frame)
    logger.info(f"[Expression] Service initialized, forwarding to {EXPRESSION_SERVICE_URL}")

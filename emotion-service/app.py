"""Emotion Analysis Service — receives gallery-view frames, detects faces, classifies emotions."""

import base64
import io
import os
import asyncio
import json
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("emotion-service")

app = FastAPI(title="Emotion Analysis Service")

# ── State ──────────────────────────────────────────────────────────────────────
from emotion_state import EmotionStateManager

state = EmotionStateManager()
ws_clients: list[WebSocket] = []

USE_MODAL = os.getenv("USE_MODAL", "false").lower() == "true"


# ── Lazy-load DeepFace for local inference ─────────────────────────────────────
_deepface = None


def get_deepface():
    global _deepface
    if _deepface is None:
        logger.info("Loading DeepFace model (first call, may take a moment)...")
        from deepface import DeepFace

        _deepface = DeepFace
    return _deepface


# ── Models ─────────────────────────────────────────────────────────────────────
class VideoFrameRequest(BaseModel):
    meeting_id: str
    image_data: str  # base64 JPEG
    timestamp: float


# ── Helpers ────────────────────────────────────────────────────────────────────
def decode_frame(image_bytes: bytes):
    """Decode image bytes — tries JPEG first, falls back to H264 keyframe via OpenCV."""
    import numpy as np
    from PIL import Image

    # Try as JPEG/PNG first
    try:
        img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        if img.size > 0:
            return img
    except Exception:
        pass

    # Fall back to OpenCV imdecode (handles JPEG, PNG, and raw frame buffers)
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is not None:
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    logger.warning(f"Could not decode frame ({len(image_bytes)} bytes)")
    return None


def analyze_local(image_bytes: bytes) -> dict:
    """Run DeepFace locally on M2 Pro."""
    DeepFace = get_deepface()
    img = decode_frame(image_bytes)
    if img is None:
        return {"faces": []}
    results = DeepFace.analyze(
        img,
        actions=["emotion"],
        enforce_detection=False,
        detector_backend="opencv",
        silent=True,
    )
    if not isinstance(results, list):
        results = [results]

    return {
        "faces": [
            {
                "emotion": {k: float(v) for k, v in r["emotion"].items()},
                "dominant_emotion": r["dominant_emotion"],
                "region": {k: int(v) if isinstance(v, (int, float)) else v
                           for k, v in r.get("region", {}).items()
                           if k in ("x", "y", "w", "h")},
                "confidence": float(r.get("face_confidence", 0)),
            }
            for r in results
        ]
    }


def analyze_modal(image_bytes: bytes) -> dict:
    """Run emotion analysis on Modal cloud."""
    from modal_model import analyze_emotions

    return analyze_emotions.remote(image_bytes)


async def broadcast(data: dict):
    """Send data to all connected WebSocket clients."""
    msg = json.dumps(data)
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.post("/api/video-frame")
async def receive_video_frame(req: VideoFrameRequest):
    """Receive a gallery-view JPEG frame, detect faces, classify emotions."""
    try:
        image_bytes = base64.b64decode(req.image_data)
    except Exception:
        return JSONResponse({"error": "Invalid base64 image data"}, status_code=400)

    # Run analysis (blocking call in thread pool to avoid stalling the event loop)
    loop = asyncio.get_event_loop()
    if USE_MODAL:
        result = await loop.run_in_executor(None, analyze_modal, image_bytes)
    else:
        result = await loop.run_in_executor(None, analyze_local, image_bytes)

    faces = result.get("faces", [])
    state.update_from_frame(faces)

    payload = {
        "type": "emotion_update",
        "faces": state.get_all_faces(),
        "summary": state.get_class_summary(),
        "timestamp": req.timestamp,
    }
    await broadcast(payload)

    return {"faces_detected": len(faces), "summary": state.get_class_summary()}


@app.get("/api/emotions")
async def get_emotions():
    """Current emotion data for all tracked faces + class summary."""
    return {
        "faces": state.get_all_faces(),
        "summary": state.get_class_summary(),
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    logger.info(f"WebSocket client connected ({len(ws_clients)} total)")
    try:
        # Send current state immediately
        await ws.send_text(
            json.dumps(
                {
                    "type": "emotion_update",
                    "faces": state.get_all_faces(),
                    "summary": state.get_class_summary(),
                    "timestamp": 0,
                }
            )
        )
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info(f"WebSocket client disconnected ({len(ws_clients)} total)")


@app.get("/health")
async def health():
    return {"status": "ok", "use_modal": USE_MODAL}


@app.get("/")
async def dashboard():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    logger.info(f"Starting Emotion Service on port {port} (modal={USE_MODAL})")
    uvicorn.run(app, host="0.0.0.0", port=port)

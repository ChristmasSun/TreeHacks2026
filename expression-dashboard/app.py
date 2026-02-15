from __future__ import annotations

import io
import time
from collections import defaultdict
from dataclasses import dataclass, field

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fer.fer import FER

# ---------------------------------------------------------------------------
# FER singleton (loaded once at startup)
# ---------------------------------------------------------------------------
detector = FER(mtcnn=False)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

BUFFER_SECONDS = 30 * 60  # keep last 30 minutes of data


@dataclass
class EmotionRecord:
    timestamp: float
    emotions: dict[str, float]  # angry, disgust, fear, happy, sad, surprise, neutral
    num_faces: int = 1


@dataclass
class MeetingData:
    records: list[EmotionRecord] = field(default_factory=list)
    last_frame_time: float = 0.0
    consecutive_neutral: int = 0

    def prune(self) -> None:
        cutoff = time.time() - BUFFER_SECONDS
        self.records = [r for r in self.records if r.timestamp >= cutoff]


meetings: dict[str, MeetingData] = defaultdict(MeetingData)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Expression Dashboard")

# Enable CORS for RTMS service to post frames
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

EMOTION_KEYS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
THROTTLE_SECONDS = 2.0


# ---------------------------------------------------------------------------
# Frame ingestion
# ---------------------------------------------------------------------------
@app.post("/api/frames")
async def ingest_frame(
    frame: UploadFile = File(...),
    meeting_id: str = Form(...),
    timestamp: str = Form("0"),
):
    now = time.time()
    md = meetings[meeting_id]

    # Throttle: skip if frame arrived too soon
    if now - md.last_frame_time < THROTTLE_SECONDS:
        return JSONResponse({"status": "throttled"})
    md.last_frame_time = now

    # Decode JPEG
    raw = await frame.read()
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return JSONResponse({"status": "decode_error"}, status_code=400)

    # Run FER on image (detects all faces)
    results = detector.detect_emotions(img)
    if not results:
        return JSONResponse({"status": "no_faces"})

    # Average emotions across all detected faces
    avg: dict[str, float] = {k: 0.0 for k in EMOTION_KEYS}
    for face in results:
        for k in EMOTION_KEYS:
            avg[k] += face["emotions"].get(k, 0.0)
    num_faces = len(results)
    for k in avg:
        avg[k] /= num_faces

    ts = float(timestamp) if timestamp != "0" else now
    record = EmotionRecord(timestamp=ts, emotions=avg, num_faces=num_faces)
    md.records.append(record)
    md.prune()

    # Track consecutive neutral for boredom detection
    if avg.get("neutral", 0) > 0.7:
        md.consecutive_neutral += 1
    else:
        md.consecutive_neutral = 0

    return JSONResponse({
        "status": "ok",
        "faces": num_faces,
        "emotions": avg,
    })


# ---------------------------------------------------------------------------
# Dashboard API
# ---------------------------------------------------------------------------
@app.get("/api/emotions")
async def list_meetings():
    result = []
    for mid, md in meetings.items():
        if md.records:
            result.append({
                "meeting_id": mid,
                "record_count": len(md.records),
                "last_update": md.records[-1].timestamp,
            })
    return {"meetings": result}


@app.get("/api/emotions/{meeting_id}/current")
async def current_emotions(meeting_id: str):
    md = meetings.get(meeting_id)
    if not md or not md.records:
        return {"status": "no_data"}

    latest = md.records[-1]
    emotions = latest.emotions

    # Dominant emotion
    dominant = max(emotions, key=emotions.get)

    # Alerts
    confusion_score = (
        emotions.get("fear", 0) + emotions.get("surprise", 0) + emotions.get("sad", 0)
    ) / 3
    confusion_alert = confusion_score > 0.35
    boredom_alert = md.consecutive_neutral >= 3

    # Recent average (last 5 records for smoothing)
    recent = md.records[-5:]
    avg_emotions: dict[str, float] = {k: 0.0 for k in EMOTION_KEYS}
    for r in recent:
        for k in EMOTION_KEYS:
            avg_emotions[k] += r.emotions.get(k, 0.0)
    for k in avg_emotions:
        avg_emotions[k] /= len(recent)

    return {
        "status": "ok",
        "meeting_id": meeting_id,
        "timestamp": latest.timestamp,
        "num_faces": latest.num_faces,
        "emotions": emotions,
        "avg_emotions": avg_emotions,
        "dominant": dominant,
        "confusion_alert": confusion_alert,
        "confusion_score": round(confusion_score, 3),
        "boredom_alert": boredom_alert,
        "consecutive_neutral": md.consecutive_neutral,
        "total_records": len(md.records),
    }


@app.get("/api/emotions/{meeting_id}/timeline")
async def emotion_timeline(meeting_id: str):
    md = meetings.get(meeting_id)
    if not md or not md.records:
        return {"status": "no_data", "buckets": []}

    # Bucket by 30-second windows
    bucket_size = 30
    buckets: dict[int, list[EmotionRecord]] = defaultdict(list)
    for r in md.records:
        key = int(r.timestamp // bucket_size) * bucket_size
        buckets[key].append(r)

    timeline = []
    for ts in sorted(buckets.keys()):
        recs = buckets[ts]
        avg: dict[str, float] = {k: 0.0 for k in EMOTION_KEYS}
        total_faces = 0
        for r in recs:
            for k in EMOTION_KEYS:
                avg[k] += r.emotions.get(k, 0.0)
            total_faces += r.num_faces
        for k in avg:
            avg[k] /= len(recs)
        timeline.append({
            "timestamp": ts,
            "emotions": {k: round(v, 3) for k, v in avg.items()},
            "num_faces": total_faces // len(recs),
        })

    # Keep only last 10 minutes for charting
    cutoff = time.time() - 600
    timeline = [b for b in timeline if b["timestamp"] >= cutoff]

    return {"status": "ok", "buckets": timeline}


# ---------------------------------------------------------------------------
# Serve dashboard
# ---------------------------------------------------------------------------
@app.get("/")
async def dashboard():
    return FileResponse("static/index.html")

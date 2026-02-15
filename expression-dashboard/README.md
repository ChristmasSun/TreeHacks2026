# Expression Analysis Dashboard

Real-time facial expression analysis for Zoom meetings. Analyzes video frames from RTMS to detect student emotions (happy, sad, angry, surprised, neutral, etc.) and displays them on a live dashboard.

## Setup

```bash
cd expression-dashboard
uv sync
```

## Run

```bash
uv run uvicorn app:app --port 8001
```

Then open http://localhost:8001 in your browser.

## How It Works

1. The RTMS service (`rtms-zoom-official/`) captures gallery-view JPEG frames at ~1 frame per 3 seconds
2. Frames are POSTed to `/api/frames` on this service
3. FER (Facial Expression Recognition) detects faces and classifies emotions
4. The dashboard polls `/api/emotions/{meeting_id}/current` every 3 seconds to update charts

## API Endpoints

- `POST /api/frames` — Ingest a JPEG frame (multipart form: `frame`, `meeting_id`, `timestamp`)
- `GET /api/emotions` — List active meetings
- `GET /api/emotions/{meeting_id}/current` — Current emotion data + alerts
- `GET /api/emotions/{meeting_id}/timeline` — 30-second bucketed timeline (last 10 min)
- `GET /` — Dashboard UI

## Alerts

- **Confusion Alert**: Triggers when average of (fear + surprise + sad) > 35%
- **Boredom Alert**: Triggers when neutral > 70% for 3+ consecutive readings

## Configuration

Set `EXPRESSION_SERVICE_URL` in the RTMS service's `.env` to point to this service (defaults to `http://localhost:8001`).

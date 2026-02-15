# Zoom RTMS + HeyGen Live Transcription Setup

This integration captures live meeting transcripts via Zoom RTMS and feeds them as context to HeyGen avatars.

## Architecture

```
Zoom Meeting
    ↓ (webhook: meeting.rtms_started)
RTMS Service (rtms-service/)
    ↓ (WebSocket connection to Zoom RTMS)
Live Transcript Stream
    ↓ (HTTP POST to Python backend)
Python Backend (backend/)
    ↓ (context update)
HeyGen Avatar
    → Responds with awareness of conversation
```

## Quick Start

### 1. Configure Environment

Copy the environment template:
```bash
cd rtms-service
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Required: Zoom credentials from your Zoom App
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_SECRET_TOKEN=your_webhook_secret_token

# Python backend URL
PYTHON_BACKEND_URL=http://localhost:8000

# Optional: Deepgram for TTS
DEEPGRAM_API_KEY=your_deepgram_key
```

### 2. Start Services

**Terminal 1 - Python Backend:**
```bash
cd backend
python -m uvicorn app:app --reload --port 8000
```

**Terminal 2 - RTMS Service:**
```bash
cd rtms-service
npm start
```

**Terminal 3 - Expose Webhook (for development):**
```bash
ngrok http 3002
```

### 3. Configure Zoom App

1. Go to [Zoom App Marketplace](https://marketplace.zoom.us/develop/create)
2. Create or edit your **General App**
3. In **Features** → **Event Subscriptions**:
   - Add webhook URL: `https://your-ngrok-url.ngrok.io/webhook`
   - Subscribe to events:
     - `meeting.rtms_started`
     - `meeting.rtms_stopped`
4. In **Scopes**, add:
   - `meeting:read:meeting_audio`
   - `meeting:read:meeting_transcript`

### 4. Enable RTMS for Meetings

RTMS must be enabled at the account level. Contact Zoom or post in [Zoom Developer Forum](https://devforum.zoom.us/) to request access.

## API Endpoints

### RTMS Service (Port 3002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Active RTMS sessions |
| `/webhook` | POST | Zoom webhook events |
| `/ws` | WS | Frontend WebSocket |

### Python Backend (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rtms/session-start` | POST | RTMS session started |
| `/api/rtms/session-stop` | POST | RTMS session stopped |
| `/api/rtms/transcript` | POST | Receive transcript chunk |
| `/api/rtms/session/{uuid}/transcripts` | GET | Get recent transcripts |

## How It Works

### 1. Meeting Starts with RTMS
```
Zoom → Webhook: meeting.rtms_started
         ↓
RTMS Service receives { meeting_uuid, rtms_stream_id, server_urls }
         ↓
Creates RTMSClient, connects to Zoom's WebSocket servers
```

### 2. Transcripts Flow
```
Zoom RTMS WebSocket → msg_type: 17 (TRANSCRIPT)
         ↓
RTMSClient emits 'transcript' event
         ↓
HeyGenBridge.forwardTranscript() → POST /api/rtms/transcript
         ↓
Python backend stores in RTMSTranscriptionService
         ↓
Updates HeyGen avatar context
```

### 3. Avatar Context Update
```python
# In Python backend
await heygen_controller.update_avatar_context_from_transcript(
    room_id=1,
    speaker_name="Student",
    transcript_text="Can you explain this?",
    respond=True  # Optional: trigger avatar response
)
```

## Testing

### 1. Test Webhook Locally
```bash
curl -X POST http://localhost:3002/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "meeting.rtms_started",
    "payload": {
      "meeting_uuid": "test-meeting-123",
      "rtms_stream_id": "test-stream-456",
      "server_urls": "wss://rtms.zoom.us/ws"
    }
  }'
```

### 2. Check Active Sessions
```bash
curl http://localhost:3002/stats
```

### 3. View Transcripts
```bash
curl http://localhost:8000/api/rtms/session/test-meeting-123/transcripts
```

## File Structure

```
rtms-service/
├── index.js              # Main entry point
├── config.js             # Environment configuration
├── webhookManager.js     # Zoom webhook handler
├── heygenBridge.js       # Python backend integration
├── deepgramService.js    # TTS service (optional)
├── library/
│   └── RTMSClient.js     # RTMS WebSocket client
├── package.json
└── .env.example

backend/
├── app.py                # FastAPI with RTMS endpoints
└── services/
    ├── rtms_transcription_service.py
    └── heygen_controller.py (updated)
```

## Troubleshooting

### No Transcripts Received
1. Check RTMS is enabled for your Zoom account
2. Verify webhook URL is correct
3. Check RTMS service logs for connection errors
4. Ensure meeting has audio/transcription enabled

### WebSocket Connection Fails
1. Verify `ZOOM_CLIENT_ID` and `ZOOM_CLIENT_SECRET` are correct
2. Check the signature generation
3. Look for errors in RTMS service console

### HeyGen Not Updating
1. Check Python backend is running
2. Verify `/api/rtms/transcript` endpoint works
3. Check HeyGen controller has active session for the room

## Next Steps

1. **Add Whisper Integration**: Process raw audio through Whisper for better accuracy
2. **Smart Response Triggers**: Use LLM to detect when avatar should respond
3. **Multi-Language Support**: Configure RTMS language parameter
4. **Production Deployment**: Deploy to cloud with proper SSL certificates

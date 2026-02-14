# Zoom Bot Service

Node.js microservice for managing Zoom Meeting SDK bots that join meetings programmatically.

## Overview

This service creates and manages virtual Zoom participants (bots) that:
- Join Zoom meetings as participants
- Join specific breakout rooms
- Capture and stream audio to HeyGen/Deepgram
- Play audio from HeyGen avatars

## Architecture

```
Python Backend (FastAPI)
  ↓ HTTP/REST
Zoom Bot Service (Node.js)
  ↓ Zoom Meeting SDK
Zoom Meeting
```

## Setup

### 1. Install Dependencies

```bash
cd zoom-bot-service
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
ZOOM_SDK_KEY=your_sdk_key
ZOOM_SDK_SECRET=your_sdk_secret
PORT=3001
PYTHON_BACKEND_URL=http://localhost:8000
```

**Important**: Zoom SDK credentials are **different** from REST API credentials!
- Get them from: https://marketplace.zoom.us/
- Create a "Meeting SDK" app (not Server-to-Server OAuth)

### 3. Run Service

**Development:**
```bash
npm run dev
```

**Production:**
```bash
npm run build
npm start
```

## API Reference

### Health Check
```bash
GET /health
```

### Create Bot
```bash
POST /bots/create
Content-Type: application/json

{
  "meeting_number": "123456789",
  "passcode": "abc123",
  "bot_name": "AI Professor - Alice",
  "room_id": 1,
  "heygen_session_id": "session_xyz"
}

Response:
{
  "bot_id": "uuid",
  "status": "joined",
  "message": "Bot created successfully"
}
```

### List Bots
```bash
GET /bots
```

### Get Bot Info
```bash
GET /bots/:bot_id
```

### Move to Breakout Room
```bash
POST /bots/:bot_id/join-breakout-room

{
  "breakout_room_id": "room_abc"
}
```

### Play Audio
```bash
POST /bots/:bot_id/play-audio

{
  "audio_data": "base64_encoded_audio"
}
```

### Remove Bot
```bash
DELETE /bots/:bot_id
```

### Remove All Bots
```bash
DELETE /bots
```

### Statistics
```bash
GET /stats
```

## Current Status

### ✅ Implemented
- HTTP API server
- Bot management (create/remove)
- JWT signature generation
- Event system
- Graceful shutdown

### 🔄 In Progress
- Zoom Rivet SDK integration (implemented, needs testing)
- Audio routing to HeyGen/Deepgram
- Error recovery and reconnection

## Zoom Rivet SDK Integration

This service uses **Zoom Rivet SDK** for headless bot participation:

**What is Rivet?**
- Zoom's Real-Time Media SDK for building meeting bots
- Native Node.js support (no browser required)
- WebRTC-based audio/video streaming
- Official solution for programmatic meeting participation

**Key Features:**
- ✅ Join meetings as bot participant
- ✅ Send/receive audio streams
- ✅ Join breakout rooms programmatically
- ✅ Lightweight (no Puppeteer/browser overhead)
- ✅ Multiple concurrent bots per Node.js process

**Learn More:**
- GitHub: https://github.com/zoom/rivet-javascript
- Docs: https://developers.zoom.us/docs/video-sdk/

## Integration with Python Backend

The Python backend communicates with this service via HTTP:

```python
# backend/services/zoom_bot_service_client.py

async def create_bot(meeting_number, bot_name, room_id):
    response = await httpx.post(
        "http://localhost:3001/bots/create",
        json={
            "meeting_number": meeting_number,
            "bot_name": bot_name,
            "room_id": room_id
        }
    )
    return response.json()["bot_id"]
```

## Development

### Run in Development Mode
```bash
npm run dev
```

### Build TypeScript
```bash
npm run build
```

### Test API
```bash
# Health check
curl http://localhost:3001/health

# Create bot (will simulate join for now)
curl -X POST http://localhost:3001/bots/create \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_number": "123456789",
    "bot_name": "Test Bot",
    "room_id": 1
  }'

# List bots
curl http://localhost:3001/bots

# Stats
curl http://localhost:3001/stats
```

## Next Steps

1. **Implement Zoom SDK Join** - Choose integration approach (Puppeteer recommended)
2. **Audio Routing** - Capture Zoom audio, send to Deepgram/HeyGen
3. **Breakout Room Logic** - Navigate to specific breakout rooms
4. **Error Handling** - Reconnection, failure recovery
5. **Production Deploy** - Docker, process management

## Troubleshooting

### "Missing environment variables"
- Check `.env` file exists
- Verify `ZOOM_SDK_KEY` and `ZOOM_SDK_SECRET` are set
- Remember: SDK credentials ≠ REST API credentials

### "Port 3001 already in use"
- Change `PORT` in `.env`
- Or kill existing process: `lsof -ti:3001 | xargs kill`

### Bots not actually joining Zoom
- **This is expected!** Zoom SDK integration is not yet implemented
- Bots are currently simulated for testing
- Implement one of the integration options above

## License

MIT

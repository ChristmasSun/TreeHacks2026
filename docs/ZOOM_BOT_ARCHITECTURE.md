# Zoom Bot Architecture - Implementation Plan

## The Challenge

We have:
- **Python backend** (FastAPI) - Session orchestration, HeyGen, Deepgram
- **Zoom Meeting SDK** - Available in JavaScript (Web/Node.js) and C++ (Native)

We need: Bots that join Zoom and route audio to HeyGen/Deepgram

## Solution: Hybrid Architecture (Recommended)

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Python Backend (FastAPI)                                │
│  ├─ SessionOrchestrator                                  │
│  ├─ HeyGenController                                     │
│  └─ TranscriptionService (Deepgram)                      │
└──────────────┬──────────────────────────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼──────────────────────────────────────────┐
│  Node.js Zoom Bot Service                                │
│  ├─ Zoom Meeting SDK (@zoom/meetingsdk)                  │
│  ├─ Bot Manager (spawn/manage multiple bots)             │
│  └─ Audio Router (Zoom ↔ HeyGen ↔ Deepgram)              │
└──────────────┬──────────────────────────────────────────┘
               │
         Joins Zoom Meeting
```

### Why This Approach?

✅ **Pros:**
- Uses official Zoom Meeting SDK (fully supported)
- Node.js is lightweight and fast for bot operations
- Python backend stays focused on orchestration
- Can scale bots independently
- Easy audio routing with Node.js streams

❌ **Cons:**
- Two runtimes (Python + Node.js)
- Slightly more complex deployment

### Alternative Approaches Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Puppeteer + Web SDK** | Simple, one codebase | High resource usage (Chrome per bot) | ❌ Not scalable |
| **Zoom Linux SDK + Python** | Native performance | Complex C++ bindings | ❌ High complexity |
| **Node.js Microservice** ✅ | Official SDK, lightweight | Two services | ✅ **Best balance** |

---

## Implementation Plan

### Phase 1: Node.js Bot Service (Core)

**Files to Create:**
```
zoom-bot-service/
├── package.json
├── src/
│   ├── index.ts              # Main entry point
│   ├── BotManager.ts          # Manages multiple bot instances
│   ├── ZoomBot.ts             # Individual bot logic
│   ├── AudioRouter.ts         # Audio streaming (Zoom ↔ HeyGen ↔ Deepgram)
│   └── server.ts              # HTTP API for Python backend
└── tsconfig.json
```

**API Endpoints:**
```typescript
POST /bots/create
{
  "meeting_number": "123456789",
  "passcode": "abc123",
  "bot_name": "AI Professor - Alice",
  "room_id": 1,
  "heygen_session_id": "xyz",
  "deepgram_config": {...}
}

Response:
{
  "bot_id": "bot_001",
  "status": "joining",
  "zoom_participant_id": "..."
}

POST /bots/:bot_id/join-breakout-room
{
  "breakout_room_id": "abc123"
}

DELETE /bots/:bot_id
// Stop and cleanup bot
```

### Phase 2: Python Integration

**Update SessionOrchestrator:**
```python
# backend/services/session_orchestrator.py

async def create_breakout_session(...):
    # ... existing code ...

    # After avatar deployment:
    bot_deployment_results = await self._deploy_zoom_bots(
        meeting_id=meeting_result["meeting_id"],
        breakout_rooms=breakout_rooms,
        avatar_sessions=avatar_deployment_result
    )
```

**New Service:**
```python
# backend/services/zoom_bot_service_client.py

class ZoomBotServiceClient:
    """Client for Node.js Zoom Bot Service"""

    async def create_bot(
        self,
        meeting_number: str,
        bot_name: str,
        heygen_session_id: str
    ) -> Dict[str, Any]:
        # POST to Node.js service
```

### Phase 3: Audio Routing

**Audio Flow:**
```
Student speaks in Zoom
  ↓
Zoom Bot captures audio (PCM)
  ├─→ Stream to Deepgram (transcription)
  └─→ Stream to HeyGen (avatar listening)
       ↓
HeyGen responds (audio)
  ↓
Zoom Bot plays audio in Zoom
  ↓
Student hears avatar
```

**Implementation in Node.js:**
```typescript
// zoom-bot-service/src/AudioRouter.ts

class AudioRouter {
  async routeAudioFromZoom(audioChunk: Buffer) {
    // Fork audio stream
    await Promise.all([
      this.sendToDeepgram(audioChunk),  // Transcription
      this.sendToHeyGen(audioChunk)      // Avatar listening
    ]);
  }

  async routeAudioToZoom(heygenAudio: Buffer) {
    // HeyGen response → Zoom playback
    await this.zoomBot.playAudio(heygenAudio);
  }
}
```

---

## Detailed Implementation Steps

### Step 1: Create Node.js Bot Service

**Time:** 2-3 hours

**1.1 Initialize Project:**
```bash
mkdir zoom-bot-service
cd zoom-bot-service
npm init -y
npm install @zoom/meetingsdk express cors ws dotenv
npm install -D typescript @types/node @types/express ts-node
```

**1.2 Zoom Meeting SDK Setup:**
```typescript
// src/ZoomBot.ts
import ZoomMtgEmbedded from '@zoom/meetingsdk/embedded';

class ZoomBot {
  private client: typeof ZoomMtgEmbedded;

  async join(config: JoinConfig) {
    // Initialize SDK
    this.client = ZoomMtgEmbedded.createClient();

    // Join meeting
    await this.client.init({ ... });
    await this.client.join({
      sdkKey: process.env.ZOOM_SDK_KEY,
      signature: this.generateSignature(),
      meetingNumber: config.meetingNumber,
      userName: config.botName,
      password: config.passcode
    });

    // Setup audio stream listeners
    this.setupAudioCapture();
  }
}
```

### Step 2: Audio Stream Capture

**Time:** 1-2 hours

**2.1 Capture Audio from Zoom:**
```typescript
// Use Zoom SDK audio stream API
private setupAudioCapture() {
  this.client.on('audio-data', (audioData) => {
    // audioData is PCM format
    this.audioRouter.routeAudioFromZoom(audioData);
  });
}
```

**2.2 Send Audio to Services:**
```typescript
// src/AudioRouter.ts
async sendToDeepgram(audioChunk: Buffer) {
  // Stream to Python backend
  await fetch('http://localhost:8000/api/audio/process', {
    method: 'POST',
    body: JSON.stringify({
      room_id: this.roomId,
      audio_data: audioChunk.toString('base64')
    })
  });
}
```

### Step 3: Integrate with Python Backend

**Time:** 1 hour

**3.1 Create Bot Service Client:**
```python
# backend/services/zoom_bot_service_client.py

class ZoomBotServiceClient:
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url

    async def create_bot(
        self,
        meeting_number: str,
        passcode: str,
        bot_name: str,
        room_id: int,
        heygen_session_id: str
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/bots/create",
                json={
                    "meeting_number": meeting_number,
                    "passcode": passcode,
                    "bot_name": bot_name,
                    "room_id": room_id,
                    "heygen_session_id": heygen_session_id
                }
            )
            result = response.json()
            return result["bot_id"]
```

**3.2 Update SessionOrchestrator:**
```python
# Add to __init__
self.zoom_bot_client = ZoomBotServiceClient()

# In create_breakout_session, after avatar deployment:
for room, deployment in zip(breakout_rooms, avatar_deployments):
    bot_id = await self.zoom_bot_client.create_bot(
        meeting_number=meeting_result["meeting_id"],
        passcode="",
        bot_name=f"AI Professor - {room.student.name}",
        room_id=room.id,
        heygen_session_id=deployment["session_id"]
    )

    room.zoom_bot_id = bot_id
    await db.commit()
```

---

## Timeline

| Task | Time | Status |
|------|------|--------|
| 1. Node.js bot service setup | 2-3 hours | 🔄 Next |
| 2. Zoom SDK integration | 2-3 hours | 📅 Pending |
| 3. Audio routing implementation | 2-3 hours | 📅 Pending |
| 4. Python client integration | 1 hour | 📅 Pending |
| 5. Testing & debugging | 2-3 hours | 📅 Pending |
| **Total** | **9-13 hours** | **1-2 days** |

---

## Quick Start (MVP)

For fastest path to demo:

**Option 1: Simplified Bot (No Audio Routing)**
- Bot joins Zoom ✅
- Bot joins breakout room ✅
- Bot presence visible ✅
- Audio routing = Phase 2 ⏭️

**Time:** 3-4 hours

**Option 2: Full Implementation**
- Everything above ✅
- Audio capture ✅
- Deepgram integration ✅
- HeyGen integration ✅

**Time:** 9-13 hours

---

## Next Steps

1. **Create zoom-bot-service** (Node.js)
2. **Implement ZoomBot class** (joins meetings)
3. **Create HTTP API** (Python communication)
4. **Test bot joining**
5. **Add audio routing**
6. **Integrate with HeyGen/Deepgram**

Ready to start? I'll begin with the Node.js bot service.

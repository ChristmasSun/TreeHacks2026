# Architecture

## System Overview

This system automates Zoom breakout rooms with AI professor clones (HeyGen avatars) for personalized 1-on-1 student tutoring at scale. A professor starts a session, and the system creates a Zoom meeting, assigns students to breakout rooms, deploys AI avatars into each room, and transcribes every conversation in real time.

There are four independently deployed components:

```
┌──────────────────────────────────────────────────────────────┐
│  Electron App  (React + TypeScript)                          │
│  Student registration, professor dashboard, avatar player    │
└────────────────────┬─────────────────────────────────────────┘
                     │ WebSocket (ws://backend:8000/ws)
┌────────────────────▼─────────────────────────────────────────┐
│  Python Backend  (FastAPI)                                    │
│  Session orchestration, DB, transcription, LLM, TTS          │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────────────────┐ │
│  │SessionOrch.  │ │HeyGenCtrl.  │ │TranscriptionService   │ │
│  │ (lifecycle)  │ │ (avatars)   │ │ (Deepgram streams)    │ │
│  └──────┬───────┘ └──────┬──────┘ └───────────┬───────────┘ │
│         │                │                     │             │
│    Zoom REST API    HeyGen API v2         Deepgram WS       │
└─────────┬────────────────┬─────────────────────┬─────────────┘
          │           HTTP  │                     │
┌─────────▼────────────────▼───────────────────┐ │
│  Zoom Bot Service  (Node.js + Zoom SDK)      │ │
│  Headless bots join meetings/breakout rooms   │ │
│  Audio capture → backend, audio playback ← HG│ │
└──────────────────────────────────────────────┘ │
                                                 │
┌────────────────────────────────────────────────▼─┐
│  RTMS Service  (Node.js)                          │
│  Zoom Real-Time Messaging for live transcription  │
│  Bridges transcripts → HeyGen avatar context      │
└───────────────────────────────────────────────────┘
```

## Components

### 1. Electron App (`src/electron/`)

Desktop application with two modes: student client and professor dashboard.

| Directory | Purpose |
|-----------|---------|
| `main/index.ts` | Electron main process, window lifecycle |
| `main/websocket-client.ts` | Persistent WebSocket to Python backend with auto-reconnect |
| `main/ipc-handlers.ts` | IPC bridge between main and renderer |
| `main/preload.ts` | Context bridge for secure renderer access |
| `renderer/App.tsx` | Student app: registration form + waiting state + avatar player |
| `renderer/components/Dashboard.tsx` | Professor: create sessions, validate credentials, copy join URLs |
| `renderer/components/SessionMonitor.tsx` | Real-time grid of all breakout rooms with status indicators |
| `renderer/components/HeyGenAvatar.tsx` | Embedded HeyGen avatar player (LiveKit WebRTC) |
| `renderer/heygen-avatar.html` | Standalone avatar HTML for popup window mode |

UI is a frosted-glass top-bar (Cluely-style) using Tailwind CSS. Window can be hidden/minimized/expanded from the system tray.

**Key dependencies**: Electron 28, React 18, `@heygen/streaming-avatar`, `livekit-client`, Zustand, Tailwind CSS.

### 2. Python Backend (`backend/`)

FastAPI server. Single process, fully async. Handles all orchestration logic, database access, and external API coordination.

#### Entry Point

`app.py` — 992 lines. Defines:

- `ConnectionManager` — tracks WebSocket connections, broadcasts messages
- WebSocket endpoint (`/ws`) with message routing to typed handlers
- REST endpoints for professors, students, sessions, RTMS, lecture context, tutoring, HeyGen tokens
- Zoom webhook receiver (`/webhook/zoom`)
- In-memory `registered_students` dict for student client tracking

#### Services (`backend/services/`)

| Service | File | Role |
|---------|------|------|
| **SessionOrchestrator** | `session_orchestrator.py` | Coordinates full session lifecycle: create Zoom meeting → deploy avatars → start transcription → monitor → cleanup |
| **ZoomManager** | `zoom_manager.py` | High-level Zoom operations: create meetings with breakout rooms, pre-assign students, generate URLs |
| **HeyGenController** | `heygen_controller.py` | Avatar lifecycle: create sessions with professor context, deploy to rooms in parallel, send messages, stop/restart |
| **ZoomBotServiceClient** | `zoom_bot_service_client.py` | HTTP client for the Node.js bot service: create/remove bots, play audio, move to breakout rooms |
| **TranscriptionService** | `transcription_service.py` | Per-room Deepgram WebSocket streams, processes audio chunks, saves finals to DB, forwards via WebSocket |
| **RTMSTranscriptionService** | `rtms_transcription_service.py` | Buffers RTMS transcript chunks, feeds context to HeyGen avatars, manages per-meeting sessions |
| **LLMService** | `llm_service.py` | Generates tutoring responses with lecture context injection |
| **TTSService** | `tts_service.py` | Text-to-speech via OpenAI or ElevenLabs |

#### Integrations (`backend/integrations/`)

| Adapter | File | External API |
|---------|------|-------------|
| **ZoomSDKAdapter** | `zoom_sdk_adapter.py` | Zoom REST API v2 — Server-to-Server OAuth, meeting CRUD, breakout rooms, participants |
| **HeyGenAPIAdapter** | `heygen_api_adapter.py` | HeyGen Interactive Avatar API v2 — streaming sessions, WebRTC, context injection |
| **DeepgramAdapter** | `deepgram_adapter.py` | Deepgram streaming transcription — WebSocket, nova-2 model, interim/final results, diarization |

#### Database (`backend/models/`)

SQLAlchemy async ORM. SQLite for development, PostgreSQL for production (Render).

**Tables**:

| Table | Key Columns | Purpose |
|-------|------------|---------|
| `professors` | name, email, zoom_user_id, heygen_avatar_id, context_documents | Professor profiles with avatar config |
| `students` | name, email, zoom_user_id | Student profiles |
| `sessions` | professor_id, meeting_id, status, configuration | Breakout session metadata |
| `breakout_rooms` | session_id, zoom_room_id, avatar_session_id, student_id, status | Room ↔ student ↔ avatar mapping |
| `transcripts` | room_id, speaker, text, confidence, extra_data | Conversation records per room |
| `student_progress` | student_id, session_id, topics_covered, confusion_points, engagement_score | Per-session learning metrics |
| `context_documents` | professor_id, file_path, content, embeddings_id | Course materials for RAG (future) |
| `session_analytics` | session_id, avg_engagement_score, common_confusion_points, summary_text | Post-session aggregate metrics |

**Relationships**: Professor → Sessions → BreakoutRooms → Transcripts. Student → BreakoutRooms, StudentProgress. Professor → ContextDocuments. Session → SessionAnalytics.

### 3. Zoom Bot Service (`zoom-bot-service/`)

Node.js microservice. Runs headless Zoom bots using the Zoom Meeting SDK + Puppeteer. Each bot is a virtual participant that can join meetings, navigate to breakout rooms, capture audio, and play audio.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health |
| `/bots/create` | POST | Create bot + join meeting |
| `/bots` | GET | List all active bots |
| `/bots/:id` | GET | Bot status |
| `/bots/:id/join-breakout-room` | POST | Move bot to specific breakout room |
| `/bots/:id/play-audio` | POST | Play audio through bot in meeting |
| `/bots/:id` | DELETE | Stop and remove bot |
| `/bots` | DELETE | Stop all bots |
| `/stats` | GET | Service statistics |

**Key dependencies**: `@zoom/meetingsdk`, Puppeteer, Express.

### 4. RTMS Service (`rtms-service/`)

Node.js service that connects to Zoom's Real-Time Messaging Service for live meeting transcription. Receives transcript streams via WebSocket and forwards them to the Python backend for avatar context injection.

| File | Purpose |
|------|---------|
| `index.js` | Express server + WebSocket for transcript distribution |
| `config.js` | Environment configuration |
| `heygenBridge.js` | Forwards transcripts to HeyGen avatars via Python backend |
| `deepgramService.js` | Deepgram TTS integration |
| `webhookManager.js` | Zoom webhook event handling |
| `library/RTMSClient.js` | WebSocket client for Zoom RTMS endpoint |

### 5. Manim Pipeline (`src/`, `prompts/`, `scripts/`)

Standalone Python CLI that generates 3Blue1Brown-style animated videos from YouTube lecture URLs. Completely independent from the breakout room system.

**Pipeline stages**: YouTube download → Whisper transcription → scene splitting (LLM) → narration generation (LLM) → TTS voice cloning → Manim code generation (LLM) → render with retry/correction → audio merge → stitch final video.

| File | Purpose |
|------|---------|
| `src/cli.py` | Interactive CLI with `--again` for quick reruns |
| `src/pipeline.py` | Main orchestration: async, parallel clip processing |
| `src/llm.py` | LLM calls via Dedalus Labs API (GPT-5.2) with retry |
| `src/render.py` | Manim code sanitization (LaTeX shims, spacing fixes) + rendering |
| `src/transcribe.py` | Whisper transcription with chunking for large files |
| `src/download.py` | yt-dlp audio extraction |
| `src/voice.py` | Voice sample extraction + Pocket TTS voice cloning |
| `scripts/continue_pipeline_from_narrations.py` | Resume pipeline from saved narration JSON |
| `scripts/compile_animation_attempts.sh` | Batch-compile animation attempt files |

**Key dependencies**: Manim 0.19.2, Pocket TTS, torchaudio, yt-dlp, httpx, scipy.

## Data Flows

### Session Creation

```
1. Professor clicks "Start Session" in Dashboard.tsx
2. WebSocket → CREATE_SESSION {professor_id, student_ids, topic, duration}
3. SessionOrchestrator.create_breakout_session():
   a. Fetch professor + students from DB
   b. ZoomManager.create_meeting_with_breakout_rooms()
      → Zoom REST API: create meeting, create rooms, pre-assign students
   c. Create Session + BreakoutRoom records in DB
   d. HeyGenController.deploy_avatars_to_rooms() (parallel)
      → For each room: create avatar session with professor context
      → ZoomBotServiceClient: create bot, join meeting, move to breakout room
   e. TranscriptionService.start_room_transcription() per room
      → Open Deepgram WebSocket stream per room
   f. Return SESSION_CREATED with meeting URLs and room assignments
4. Frontend receives → updates Dashboard + SessionMonitor
```

### Conversation (In Breakout Room)

```
Student speaks in Zoom
  → Zoom bot captures audio
  → Audio sent to Python backend (PROCESS_AUDIO)
  → TranscriptionService → Deepgram WebSocket
  → Deepgram returns transcript (interim + final)
  → Final transcripts saved to DB (Transcript table)
  → All transcripts broadcast via WebSocket (TRANSCRIPT_UPDATE)
  → SessionMonitor updates in real time

HeyGen avatar generates response
  → Avatar audio → Zoom bot → plays in meeting
  → Student hears AI professor response
```

### RTMS Transcript Flow

```
Zoom RTMS → rtms-service (Node.js WebSocket)
  → POST /api/rtms/transcript to Python backend
  → RTMSTranscriptionService buffers chunks
  → Context fed to HeyGen avatars for informed responses
  → Broadcast RTMS_TRANSCRIPT to frontend
```

## API Reference

### WebSocket Messages (ws://backend:8000/ws)

All messages use `{type: string, payload: object}` format.

#### Client → Server

| Type | Payload | Response Type |
|------|---------|---------------|
| `PING` | `{}` | `PONG` |
| `CREATE_SESSION` | `{professor_id, student_ids, topic, duration, configuration}` | `SESSION_CREATED` |
| `END_SESSION` | `{session_id}` | `SESSION_ENDED` |
| `GET_SESSION_STATUS` | `{session_id}` | `SESSION_STATUS` |
| `GET_STUDENTS` | `{}` | `STUDENTS_LIST` |
| `VALIDATE_ZOOM` | `{}` | `ZOOM_VALIDATION` |
| `VALIDATE_DEEPGRAM` | `{}` | `DEEPGRAM_VALIDATION` |
| `GET_ROOM_TRANSCRIPTS` | `{room_id, limit?}` | `ROOM_TRANSCRIPTS` |
| `PROCESS_AUDIO` | `{room_id, audio_data (base64)}` | `AUDIO_PROCESSED` |
| `REGISTER_STUDENT` | `{name, email}` | `STUDENT_REGISTERED` |
| `STUDENT_MESSAGE` | `{sessionId, studentName, message}` | `MESSAGE_RECEIVED` |
| `TRIGGER_BREAKOUT` | `{session_id?, meeting_id?}` | `BREAKOUT_TRIGGERED` |

#### Server → Client (Broadcasts)

| Type | Payload | Trigger |
|------|---------|---------|
| `SESSION_CREATED` | `{session_id, meeting_id, join_url, breakout_rooms, avatars}` | Session creation |
| `SESSION_ENDED` | `{session_id, status, total_rooms, avatars_stopped}` | Session end |
| `TRANSCRIPT_UPDATE` | `{room_id, speaker, text, confidence, is_final}` | Real-time transcription |
| `RTMS_TRANSCRIPT` | `{meeting_uuid, room_id, speaker_name, text}` | RTMS transcript chunk |
| `BREAKOUT_STARTED` | `{studentEmail, studentName, avatarSession}` | Avatar deployed for student |

### REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check with active connection count |
| GET | `/dashboard` | Serve professor dashboard HTML |
| GET | `/api/professors` | List all professors |
| GET | `/api/students` | List all students |
| GET | `/api/sessions/{id}` | Session details |
| GET | `/api/registered-students` | Currently registered student clients |
| GET | `/api/lecture-context` | Current lecture context |
| POST | `/api/lecture-context` | Set lecture context `{topic, key_points, notes}` |
| POST | `/api/tutor-response` | LLM tutoring response `{message, student_name, history}` |
| POST | `/api/tutor-audio` | LLM + TTS pipeline `{message, student_name, history, tts_provider}` |
| GET | `/api/heygen-token` | Generate HeyGen access token for frontend SDK |
| POST | `/api/trigger-breakout` | Manually trigger avatar deployment |
| POST | `/webhook/zoom` | Zoom webhook receiver |
| POST | `/api/rtms/session-start` | RTMS session started `{meeting_uuid, rtms_stream_id}` |
| POST | `/api/rtms/session-stop` | RTMS session stopped `{meeting_uuid}` |
| POST | `/api/rtms/transcript` | RTMS transcript chunk `{meeting_uuid, speaker_name, text}` |
| GET | `/api/rtms/session/{uuid}/stats` | RTMS session statistics |
| GET | `/api/rtms/session/{uuid}/transcripts` | Recent RTMS transcripts |

## Environment Variables

### Python Backend (`backend/.env`)

```
ZOOM_ACCOUNT_ID=         # Zoom Server-to-Server OAuth
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=

HEYGEN_API_KEY=          # HeyGen Interactive Avatar API

DEEPGRAM_API_KEY=        # Deepgram real-time transcription

DATABASE_URL=sqlite+aiosqlite:///./breakout_system.db   # dev
# DATABASE_URL=postgresql+asyncpg://user:pass@host/db   # prod

DEBUG=False
LOG_LEVEL=INFO
```

### Zoom Bot Service (`zoom-bot-service/.env`)

```
ZOOM_SDK_KEY=
ZOOM_SDK_SECRET=
PORT=3001
PYTHON_BACKEND_URL=http://localhost:8000
```

### RTMS Service (`rtms-service/.env`)

```
ZOOM_ACCOUNT_ID=
ZOOM_CLIENT_ID=
ZOOM_CLIENT_SECRET=
DEEPGRAM_API_KEY=
OPENAI_API_KEY=
PORT=3000
```

### Manim Pipeline (root `.env`)

```
DEDALUS_API_KEY=         # Dedalus Labs API (LLM access)
```

## Deployment

Production deployment uses Render (`render.yaml`):

- **Backend**: Python web service on Render (uvicorn, auto-deploy from git)
- **Database**: PostgreSQL on Render (free/starter tier)
- **Zoom Bot Service**: Separate Node.js service (needs Puppeteer-capable host)
- **RTMS Service**: Separate Node.js service
- **Electron App**: Packaged locally with `electron-builder`

Health check at `GET /health`. Environment variables configured in Render dashboard.

## Development

```bash
# Install all dependencies
npm install                                    # Frontend
cd backend && pip install -r requirements.txt  # Backend

# Configure environment
cd backend && cp .env.example .env             # Add API keys

# Initialize database
cd backend && python scripts/init_db.py && python scripts/seed_data.py

# Run everything
npm run dev          # Electron + FastAPI concurrently
# Or individually:
npm run dev:electron # Electron only
npm run dev:backend  # FastAPI only (port 8000)

# Manim pipeline (separate)
cd /project-root && uv run python -m src.cli
```

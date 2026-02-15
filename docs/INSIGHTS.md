# Insights

Technical observations, design decisions, known limitations, and future direction for the AI Professor Breakout Room System.

## Design Decisions

### Hybrid Microservice Architecture

The system splits into Python (orchestration + AI) and Node.js (Zoom SDK) because Zoom's Meeting SDK is JavaScript-only. Rather than trying to bridge this with a single runtime, we use two cooperating services:

- **Python backend** owns all state, orchestration, and AI integration (HeyGen, Deepgram, LLM)
- **Node.js bot service** is stateless — it just manages Zoom bot lifecycles on command

This means the Python backend is the single source of truth. The bot service is a thin executor. If the bot service crashes, the Python backend can re-deploy bots without losing session state.

The trade-off is operational complexity: two services to deploy, HTTP latency between them, and two sets of Zoom credentials to manage.

### WebSocket-First Communication

The Electron frontend communicates with the backend exclusively via WebSocket for real-time operations. REST endpoints exist only for stateless queries (`GET /api/students`) and external integrations (Zoom webhooks, RTMS).

This means:
- Session creation, monitoring, and transcript streaming all happen over a single persistent connection
- The `ConnectionManager` broadcasts to all connected clients — there's no per-user channel isolation yet
- If the WebSocket drops, the Electron client auto-reconnects, but any in-flight messages are lost

### Avatar Context Building

`HeyGenController._build_avatar_context()` constructs a prompt for each avatar that includes professor identity, student name, Socratic teaching guidelines, and optional course context. This runs once at avatar creation — the avatar doesn't get updated context during the session unless RTMS transcripts are being fed in.

The RTMS bridge (`rtms_transcription_service.py`) solves this partially by buffering live lecture transcripts and injecting them as context, so avatars can reference what the professor just said in the main room.

### Database Schema for Analytics

The schema was designed with Phase 6 (analytics) in mind, even though it's not implemented yet. `StudentProgress` tracks per-session metrics (topics covered, confusion points, engagement score), and `SessionAnalytics` stores aggregate summaries. `ContextDocument` is ready for RAG integration (Phase 5) with an `embeddings_id` field pointing to a future vector database.

This forward-looking schema means the tables exist but are mostly unpopulated in the current implementation.

### Manim Pipeline Independence

The Manim animation pipeline (`src/cli.py`, `src/pipeline.py`, etc.) is completely independent from the breakout room system. It shares the repo but has its own dependency tree (`pyproject.toml` with `uv`), its own API key (`DEDALUS_API_KEY`), and its own runtime. It doesn't touch the backend, database, or Electron app.

The connection point is conceptual: the pipeline generates lecture explanation videos that could eventually be used as course materials within breakout sessions. But right now they're separate workflows.

## How Things Actually Work

### Session Orchestration Sequence

`SessionOrchestrator.create_breakout_session()` is the most important function in the system. It runs a 6-step sequence where each step depends on the previous one, but failures are gracefully handled:

1. **DB lookup** — fetch professor and students. Hard fail if professor missing.
2. **Zoom meeting** — create meeting with breakout rooms via REST API. Hard fail if Zoom credentials invalid.
3. **DB records** — create Session + BreakoutRoom rows. Transaction-safe.
4. **Avatar deployment** — `asyncio.gather()` creates HeyGen sessions in parallel. Soft fail — session continues without avatars.
5. **Transcription** — start Deepgram streams per room. Soft fail — session continues without transcription.
6. **Return results** — includes counts of successful/failed avatars and rooms.

The key insight is that steps 4-5 are best-effort. A session with no avatars is still a valid Zoom meeting with breakout rooms. A session with no transcription still has working avatars. This graceful degradation means partial failures don't block the professor.

### Audio Routing

Audio flows through a complex path:

```
Student speaks → Zoom → Bot captures audio
  → Bot sends to Python backend (base64 over HTTP)
  → Backend decodes and sends to Deepgram WebSocket
  → Deepgram returns transcript
  → Transcript saved to DB + broadcast to frontend

Avatar responds → HeyGen generates audio
  → Python backend receives audio from HeyGen
  → Backend sends to Bot service (HTTP)
  → Bot plays audio in Zoom meeting
  → Student hears avatar
```

Each hop adds latency. The total round-trip from student question to avatar response is typically 2-4 seconds, dominated by HeyGen's response generation time.

### Manim Code Generation Loop

The Manim pipeline's most novel feature is its generate-render-correct loop:

1. LLM generates Manim Python code from a scene description + narration timing context
2. Code is sanitized (LaTeX shims for no-LaTeX environments, spacing fixes, deprecated API replacement)
3. Manim renders the code as a subprocess
4. If rendering fails, the error message + original code are sent back to the LLM for correction
5. Repeat up to `max_attempts` times (default 3)

The `render.py` sanitization is aggressive: it replaces `MathTex` with a `Text`-based shim when LaTeX isn't installed, normalizes `\over` to `\frac`, fixes deprecated `get_bottom_left()` calls, auto-inserts `buff` parameters to prevent overlapping, and ensures `rate_functions` imports are present.

The correction prompt includes a Manim cheat sheet (95 lines) covering safe API patterns, layout rules, and common pitfalls. This dramatically improves first-attempt success rates.

## Known Limitations

### Breakout Room Opening

The Zoom REST API cannot programmatically open breakout rooms — it can only create and pre-assign them. Opening requires either:
- The host clicks "Open All Rooms" in the Zoom client
- A co-host SDK bot triggers the open programmatically

The current system creates rooms but relies on the professor (host) to open them manually. The Zoom Bot Service can potentially automate this if the bot is promoted to co-host.

### No WebSocket Channel Isolation

`ConnectionManager.broadcast()` sends to all connected clients. This means:
- Every connected professor dashboard sees every session's transcripts
- Student clients receive broadcasts meant for professor dashboards
- There's no authentication or session scoping on the WebSocket

For a single-professor demo this is fine. For multi-tenant production use, messages need to be scoped to session participants.

### In-Memory State

Several pieces of state live only in memory:
- `registered_students` dict in `app.py` — lost on server restart
- `HeyGenController.active_sessions` — avatar session tracking, lost on restart
- `RTMSTranscriptionService` session buffers — lost on restart

The database persists session/room/transcript records, but active connection state (which bots are running, which Deepgram streams are open) is ephemeral. A server restart during an active session would leave orphaned Zoom bots and HeyGen sessions that need manual cleanup.

### HeyGen Audio Integration Gap

The HeyGen avatar sessions are created and configured, but the actual audio routing between HeyGen's WebRTC stream and the Zoom bot's audio is not fully wired. The `play_avatar_audio_in_zoom()` method exists but depends on the bot service implementing audio injection, which requires the Zoom Meeting SDK's audio APIs.

Current workaround: students interact with HeyGen avatars directly through the Electron app's embedded player (`HeyGenAvatar.tsx`), bypassing Zoom audio entirely.

### Transcription Without Audio Source

`TranscriptionService.start_room_transcription()` opens a Deepgram WebSocket stream, but audio must be actively pushed via `process_audio_chunk()`. Without the HeyGen→Zoom audio bridge working, there's no automatic audio feed. The `PROCESS_AUDIO` WebSocket message exists as the manual trigger.

### Manim Pipeline Reliability

LLM-generated Manim code has inherent reliability issues:
- Complex scenes (many objects, transforms) fail more often than simple ones
- LaTeX rendering requires a TeX installation — the shim fallback uses `Text()` which can't render real math
- The 3-attempt correction loop helps but doesn't guarantee success
- `fix_spacing_issues` injects default `buff` values even when the LLM intentionally omitted them
- `ensure_rate_functions_usage` regex matches inside strings and comments, potentially corrupting code

### MIME Type in Transcription

The `timestamp_audio()` function in `transcribe.py` now correctly infers MIME type from file extension (fixed in latest commit). Previously it hardcoded `audio/mpeg` for all uploads, which could cause issues when sending `.wav` files from the TTS pipeline.

## Cost Profile

Per breakout session (estimated):

| Service | Unit Cost | Example (5 students, 20 min) |
|---------|-----------|------------------------------|
| HeyGen Interactive Avatar | ~$0.03/min per avatar | $3.00 |
| Deepgram Transcription | $0.0043/min per stream | $0.43 |
| Zoom API | Free (no per-use fees) | $0.00 |
| LLM (tutoring responses) | ~$0.01/response | $0.50 (est. 50 responses) |
| **Total** | | **~$3.93** |

HeyGen dominates costs. For a 30-student class with 20-minute breakout sessions, expect ~$24 per session.

The Manim pipeline costs are separate and dominated by LLM calls for code generation (~$0.05-0.10 per scene, with 10-16 scenes per lecture = $0.50-1.60 per video).

## What's Not Built Yet

These are referenced in the codebase (schemas exist, TODOs in code) but not implemented:

1. **Context Engine / RAG** (Phase 5) — `ContextDocument` table exists but no ingestion, embedding, or retrieval logic. `embeddings_id` column is unused.

2. **Analytics Generation** (Phase 6) — `SessionAnalytics` and `StudentProgress` tables exist but are never populated. `monitor_session_health()` returns a stub. No confusion detection, engagement scoring, or topic coverage analysis.

3. **Document Upload UI** — No frontend for professors to upload course materials.

4. **Session Scoping** — No multi-tenant isolation. All WebSocket clients see all events.

5. **Auto-Open Breakout Rooms** — Requires SDK bot with co-host privileges.

6. **Electron Packaging** — `electron-builder` is configured but no build/release pipeline exists.

7. **Alembic Migrations** — Database schema changes require manual `init_db.py` re-runs. No migration history.

## File Index

Quick reference for finding things:

| What | Where |
|------|-------|
| FastAPI app + all handlers | `backend/app.py` |
| Session lifecycle | `backend/services/session_orchestrator.py` |
| Avatar management | `backend/services/heygen_controller.py` |
| Zoom API calls | `backend/integrations/zoom_sdk_adapter.py` |
| HeyGen API calls | `backend/integrations/heygen_api_adapter.py` |
| Deepgram streaming | `backend/integrations/deepgram_adapter.py` |
| Transcription service | `backend/services/transcription_service.py` |
| RTMS transcript handling | `backend/services/rtms_transcription_service.py` |
| Database models (8 tables) | `backend/models/models.py` |
| DB engine setup | `backend/models/database.py` |
| Professor dashboard | `src/electron/renderer/components/Dashboard.tsx` |
| Room status grid | `src/electron/renderer/components/SessionMonitor.tsx` |
| Student app | `src/electron/renderer/App.tsx` |
| Electron main process | `src/electron/main/index.ts` |
| WebSocket client | `src/electron/main/websocket-client.ts` |
| Zoom bot service | `zoom-bot-service/src/index.ts` |
| RTMS service | `rtms-service/index.js` |
| RTMS WebSocket client | `rtms-service/library/RTMSClient.js` |
| Manim pipeline entry | `src/cli.py` |
| Manim orchestration | `src/pipeline.py` |
| Manim code sanitization | `src/render.py` |
| Voice cloning + TTS | `src/voice.py` |
| Whisper transcription | `src/transcribe.py` |
| LLM prompts | `prompts/*.txt` |
| Render deploy config | `render.yaml` |
| Project roadmap | `PLAN.md` |

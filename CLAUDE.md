# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Two independent systems sharing one repo:

1. **AI Professor Breakout Room System** — Automated Zoom breakout rooms with HeyGen AI professor clones for 1-on-1 student tutoring at scale. Four cooperating services: Electron app, Python backend (FastAPI), Node.js Zoom bot service, Node.js RTMS service.
2. **Manim Video Pipeline** — Standalone CLI that generates 3Blue1Brown-style animated videos from YouTube lectures. Completely independent from the breakout room system.

## Commands

### Development (breakout room system)

```bash
npm run dev                    # Electron + FastAPI backend concurrently
npm run dev:electron           # Electron app only
npm run dev:backend            # FastAPI backend only (uvicorn, port 8000)
cd zoom-bot-service && npm run dev    # Zoom bot service (port 3001)
cd rtms-zoom-official && npm start    # RTMS service (port 3000)
```

### Database

```bash
cd backend && uv run python scripts/init_db.py     # Create tables
cd backend && uv run python scripts/seed_data.py   # Seed test data
```

No Alembic migrations — schema changes require re-running `init_db.py`.

### Manim pipeline

```bash
uv run python -m src.cli              # Interactive CLI
uv run python -m src.cli --again      # Reuse cached parameters
```

### Build & quality

```bash
npm run build                  # Build Electron app (electron-vite)
npm run build:electron         # Package with electron-builder
npm run typecheck              # tsc --noEmit
npm run lint                   # ESLint on src/
cd zoom-bot-service && npm run build  # Compile TypeScript
```

No test suite exists (no pytest, no vitest/jest configured).

## Python (Manim pipeline & backend)

Use **uv** for all Python package management and running programs. Python 3.12+ required. Dependencies in `pyproject.toml` (locked in `uv.lock`).

## Architecture

### Service communication

```
Electron App ←—WebSocket (ws://localhost:8000/ws)—→ Python Backend (FastAPI)
                                                      ├─→ Zoom REST API
                                                      ├─→ HeyGen API v2
                                                      ├─→ Deepgram streaming WS
                                                      ├─→ Zoom Bot Service (HTTP, port 3001)
                                                      └─→ RTMS Service (HTTP, port 3000)
```

- **WebSocket-first**: All real-time operations (session lifecycle, transcription, monitoring) go over a single persistent WebSocket. REST endpoints are only for stateless queries and external webhooks.
- **Python backend is the single source of truth** — the Node.js bot service is a stateless executor of Zoom SDK operations.
- **Graceful degradation**: Avatar deployment and transcription are soft-fail. A session without working avatars is still a valid Zoom meeting with breakout rooms.

### Key entry points

| What | Where |
|------|-------|
| FastAPI app + WebSocket handlers | `backend/app.py` |
| Session lifecycle orchestration | `backend/services/session_orchestrator.py` |
| Avatar management | `backend/services/heygen_controller.py` |
| Zoom/HeyGen/Deepgram API adapters | `backend/integrations/` |
| Database models (8 tables) | `backend/models/models.py` |
| Electron main process | `src/electron/main/index.ts` |
| Professor dashboard UI | `src/electron/renderer/components/Dashboard.tsx` |
| Manim pipeline orchestration | `src/pipeline.py` |
| Manim code sanitization + rendering | `src/render.py` |

### WebSocket message format

All messages: `{type: string, payload: object}`. Key types: `CREATE_SESSION`, `END_SESSION`, `TRANSCRIPT_UPDATE`, `RTMS_TRANSCRIPT`, `PROCESS_AUDIO`, `REGISTER_STUDENT`. No per-user channel isolation — `ConnectionManager.broadcast()` sends to all connected clients.

### In-memory state

`registered_students`, `HeyGenController.active_sessions`, and RTMS session buffers live only in memory. A server restart during an active session orphans Zoom bots and HeyGen sessions.

## Environment Variables

Three separate `.env` files required:

- **`backend/.env`** — `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `HEYGEN_API_KEY`, `DEEPGRAM_API_KEY`, `CEREBRAS_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`
- **`zoom-bot-service/.env`** — `ZOOM_SDK_KEY`, `ZOOM_SDK_SECRET`, `HEYGEN_API_KEY`, `CEREBRAS_API_KEY`, `DEEPGRAM_API_KEY`, `PYTHON_BACKEND_URL`
- **Root `.env`** — `DEDALUS_API_KEY` (for Manim pipeline LLM calls via Dedalus Labs)

## Deployment

Production on Render (`render.yaml`): Python backend + PostgreSQL. Zoom bot service and RTMS service are separate Node.js deployments. Electron app is packaged locally.

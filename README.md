# AI Professor - Scalable Personalized Education

> Transform any lecture into an interactive AI-powered learning experience with avatar tutors, auto-generated quizzes, and 3Blue1Brown-style explainer videos.

[![Built at TreeHacks 2026](https://img.shields.io/badge/Built%20at-TreeHacks%202026-blue)]()
[![Phase 1](https://img.shields.io/badge/Phase%201-Complete-success)]()
[![Phase 2](https://img.shields.io/badge/Phase%202-Complete-success)]()
[![Phase 3](https://img.shields.io/badge/Phase%203-Complete-success)]()
[![Quiz Bot](https://img.shields.io/badge/Quiz%20Bot-Complete-success)]()
[![Manim Pipeline](https://img.shields.io/badge/Manim%20Pipeline-Complete-success)]()

## The Problem

Professors can't give personalized 1-on-1 attention to hundreds of students. Office hours are limited, and students often struggle with concepts without immediate help.

## Our Solution

An AI-powered professor toolkit that:
1. **Clones the professor** as an AI avatar that can tutor students individually
2. **Generates animated explainers** from any lecture (3Blue1Brown style)
3. **Creates interactive quizzes** delivered via Zoom Team Chat
4. **Provides real-time analytics** on student understanding

---

## Features

### 1. HeyGen AI Avatar Tutoring
- Professor's likeness cloned as interactive AI avatar
- Real-time lip-sync and natural conversation
- Joins Zoom breakout rooms to tutor students 1-on-1
- Context-aware responses using lecture transcripts

### 2. Manim Video Generation Pipeline
Turn any YouTube lecture into animated educational content:
```
YouTube URL → Transcribe → Scene Split → Manim Animations → Voice Clone → Final Video
```
- **Whisper transcription** via Dedalus API
- **LLM scene planning** - intelligently splits lectures into concept-based scenes
- **Auto-generated Manim code** - creates 3Blue1Brown-style animations
- **Voice cloning** with PocketTTS - maintains the professor's voice
- **Parallel rendering** - generates multiple scenes concurrently

### 3. Interactive Quiz System
- **Zoom Team Chat Chatbot** - students type `/makequiz` to start
- **Auto-generated questions** from lecture concepts using Cerebras LLM
- **Interactive button cards** - A/B/C/D answer buttons
- **Video on wrong answer** - plays the relevant Manim explainer scene
- **Progress tracking** - scores and concepts to review

### 4. Real-Time Meeting Integration
- **Zoom RTMS** (Real-Time Media Streams) for live transcription
- **WebSocket architecture** - Render service broadcasts to local dashboard
- **Live transcript accumulation** per meeting
- **Demeanor/engagement analysis** (extensible)

### 5. Professor Dashboard
- Frosted glass Electron UI
- One-click session start
- Real-time student analytics
- Quiz trigger buttons
- Meeting management

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PROFESSOR DASHBOARD                                 │
│                         (Electron + React + Tailwind)                           │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │ WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PYTHON BACKEND                                      │
│                            (FastAPI + SQLite)                                    │
│                                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Zoom API  │  │  HeyGen API │  │ Cerebras LLM│  │  Quiz Session Manager   │ │
│  │  (meetings) │  │  (avatars)  │  │ (generation)│  │  (state per student)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  Zoom Meeting │         │  Render (RTMS)  │         │  Zoom Team Chat │
│               │◄───────►│   Node.js       │◄───────►│    Chatbot      │
│  - Breakouts  │  RTMS   │   - Webhooks    │   WS    │  - /makequiz    │
│  - Avatars    │  WS     │   - Transcripts │         │  - Buttons      │
└───────────────┘         └─────────────────┘         └─────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Electron, React, TypeScript, Tailwind CSS |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, asyncio |
| **RTMS Service** | Node.js, Express, WebSocket |
| **Video Pipeline** | Manim, FFmpeg, PocketTTS |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Deployment** | Render (cloud), uv (Python pkg mgmt) |

### APIs & Services

| Service | Purpose |
|---------|---------|
| **Zoom REST API** | Meeting creation, breakout rooms, user management |
| **Zoom RTMS** | Real-time audio/video/transcript streams |
| **Zoom Team Chat** | Chatbot for interactive quizzes |
| **HeyGen** | AI avatar generation and streaming |
| **Deepgram** | Speech-to-text, text-to-speech |
| **Cerebras** | Fast LLM inference (Llama 3.3 70B) |
| **Dedalus** | Whisper API for transcription |
| **PocketTTS** | Voice cloning for narration |
| **HuggingFace** | Model hosting for TTS |

---

## Project Structure

```
TreeHacks2026/
├── src/                              # Manim video pipeline
│   ├── pipeline.py                   # Main orchestration
│   ├── downloader.py                 # YouTube audio download
│   ├── transcribe.py                 # Whisper transcription
│   ├── scene_splitter.py             # LLM-based scene planning
│   ├── clip_generator.py             # Manim code generation
│   ├── voice.py                      # TTS with voice cloning
│   └── stitcher.py                   # Final video assembly
│
├── backend/                          # Python backend
│   ├── app.py                        # FastAPI main app
│   ├── run_chatbot_client.py         # Quiz WebSocket client
│   ├── services/
│   │   ├── render_ws_client.py       # Connects to Render WebSocket
│   │   ├── chatbot_ws_handler.py     # Handles /makequiz commands
│   │   ├── quiz_generator.py         # LLM quiz generation
│   │   ├── quiz_session_manager.py   # Per-student quiz state
│   │   ├── zoom_chatbot_service.py   # Zoom API message sending
│   │   ├── heygen_controller.py      # Avatar management
│   │   ├── session_orchestrator.py   # Meeting lifecycle
│   │   └── llm_service.py            # Cerebras/OpenAI wrapper
│   └── models/                       # SQLAlchemy models
│
├── rtms-zoom-official/               # Render-deployed Node.js service
│   ├── index.js                      # Express + webhook handlers
│   ├── frontendWss.js                # WebSocket broadcasting
│   └── library/                      # RTMS SDK wrappers
│
├── frontend/                         # Electron app (if separate)
│
├── outputs/                          # Generated content (gitignored)
│   └── {topic-name}/
│       ├── audio.mp3
│       ├── transcript.txt
│       ├── scene_plan.json
│       ├── quiz_questions.json
│       └── videos/
│
├── prompts/                          # LLM prompt templates
│
└── docs/                             # Documentation
    ├── QUIZ_INTEGRATION.md           # Quiz system guide
    ├── QUICKSTART.md
    └── DEPLOYMENT.md
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- uv (Python package manager)
- FFmpeg
- LaTeX (for Manim)

### 1. Clone and Install

```bash
git clone https://github.com/ChristmasSun/TreeHacks2026.git
cd TreeHacks2026

# Python dependencies
uv sync

# Node dependencies (for RTMS service)
cd rtms-zoom-official && npm install && cd ..
```

### 2. Configure Environment

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# RTMS Service
cp rtms-zoom-official/.env.example rtms-zoom-official/.env
# Edit with Zoom credentials
```

Required API keys:
- `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `ZOOM_ACCOUNT_ID`
- `ZOOM_CHATBOT_CLIENT_ID`, `ZOOM_CHATBOT_CLIENT_SECRET`, `ZOOM_BOT_JID`
- `HEYGEN_API_KEY`
- `CEREBRAS_API_KEY`
- `DEDALUS_API_KEY`
- `HF_TOKEN` (HuggingFace for PocketTTS)

### 3. Generate Videos from a Lecture

```bash
export DEDALUS_API_KEY="your-key"
export HF_TOKEN="your-huggingface-token"

uv run python -c "
import asyncio
from src.pipeline import run

asyncio.run(run(
    'https://www.youtube.com/watch?v=YOUR_VIDEO_ID',
    'outputs/your-topic',
    clip_concurrency=4
))
"
```

### 4. Run the Quiz Chatbot

```bash
# Set quiz data directory
export QUIZ_DATA_DIR=outputs/your-topic

# Start the WebSocket client
python backend/run_chatbot_client.py
```

Then in Zoom Team Chat, message your bot with `/makequiz`.

### 5. Run the Full System

```bash
# Terminal 1: Backend
cd backend && uvicorn app:app --reload --port 8000

# Terminal 2: RTMS Service (or deploy to Render)
cd rtms-zoom-official && node index.js

# Terminal 3: Frontend
npm run dev
```

---

## How It Works

### Video Generation Flow

1. **Download** - Extracts audio from YouTube video
2. **Transcribe** - Whisper API converts speech to text with timestamps
3. **Scene Split** - LLM analyzes transcript, identifies key concepts, plans scenes
4. **Generate Code** - LLM writes Manim Python code for each scene
5. **Voice Clone** - PocketTTS extracts speaker voice sample, generates narration
6. **Render** - Manim renders animations, FFmpeg merges with voiceover
7. **Stitch** - Combines all scenes into final video

### Quiz Flow

1. **User** types `/makequiz` in Zoom Team Chat
2. **Zoom** sends webhook to Render
3. **Render** broadcasts via WebSocket to local Python
4. **Python** loads quiz JSON, creates session, sends intro card
5. **User** clicks "Start Quiz" button
6. **Python** sends first question with A/B/C/D buttons
7. **User** clicks answer
8. **If wrong** → Python triggers video playback, sends explanation
9. **If right** → Python sends next question
10. **At end** → Python sends score summary

### WebSocket Architecture

```
Zoom Webhook → Render (HTTPS) → WebSocket broadcast → Local Python
                                                           ↓
                                               Zoom API (send messages)
```

This allows the Python backend to run locally while receiving Zoom events through Render.

---

## Documentation

| Document | Description |
|----------|-------------|
| [QUIZ_INTEGRATION.md](./docs/QUIZ_INTEGRATION.md) | Complete guide to video + quiz integration |
| [QUICKSTART.md](./docs/QUICKSTART.md) | Step-by-step setup guide |
| [DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Deploy to Render |
| [PLAN.md](./PLAN.md) | Project roadmap and phases |

---

## Sample Outputs

Videos generated from:
- **Think Fast, Talk Smart** (Stanford communication lecture) - 14 scenes
- **Mathematics Gives You Wings** (fluid dynamics lecture) - 16 scenes
- **Human Behavioral Biology** (Sapolsky lecture) - 10 scenes

Each generates:
- Animated Manim videos per concept
- Quiz questions linked to videos
- Voice-cloned narration

---

## Team

Built at **TreeHacks 2026** by:
- Ved
- Christmas Sun

---

## License

MIT

---

## Acknowledgments

- [Manim Community](https://www.manim.community/) - Animation engine
- [3Blue1Brown](https://www.3blue1brown.com/) - Inspiration for visual style
- [Zoom Developer Platform](https://developers.zoom.us/) - Meeting & chat APIs
- [HeyGen](https://www.heygen.com/) - AI avatar technology
- [Cerebras](https://www.cerebras.net/) - Fast LLM inference

# AI Professor Clone Breakout Room System

> Automated Zoom breakout rooms with HeyGen AI professor clones for personalized student support

[![Phase 1](https://img.shields.io/badge/Phase%201-Complete-success)]()
[![Phase 2](https://img.shields.io/badge/Phase%202-Complete-success)]()
[![Phase 3](https://img.shields.io/badge/Phase%203-Complete-success)]()
[![Quiz Bot](https://img.shields.io/badge/Quiz%20Bot-Complete-success)]()
[![Manim Pipeline](https://img.shields.io/badge/Manim%20Pipeline-Complete-success)]()

## Quick Links

- **[📋 Project Plan](./PLAN.md)** - Complete project roadmap and status
- **[🚀 Quick Start Guide](./docs/QUICKSTART.md)** - Get started in 5 minutes
- **[📚 Full Documentation](./docs/README.md)** - Complete documentation
- **[🔧 Deployment Guide](./docs/DEPLOYMENT.md)** - Deploy to Render
- **[🎬 Quiz Integration Guide](./docs/QUIZ_INTEGRATION.md)** - Manim videos + Zoom quizzes

## What is This?

An educational tool that uses AI to provide personalized 1-on-1 support to students at scale. When a professor starts a session:

1. **Automatic Breakout Rooms** - Creates Zoom breakout rooms for each student
2. **AI Professor Clones** - HeyGen avatars join each room to help students
3. **Smart Conversations** - Real-time transcription and context-aware responses
4. **Analytics Dashboard** - Track confusion points and student progress
5. **Interactive Quizzes** - Auto-generated quizzes sent via Zoom Team Chat with video explanations
6. **3Blue1Brown-Style Videos** - Manim pipeline generates animated explainer videos from YouTube lectures

## Architecture

```
Electron UI (Top Bar) ←→ WebSocket ←→ Python Backend (localhost:8000)
                                            ├─ Zoom REST API (meetings)
                                            ├─ Zoom Team Chat Chatbot API (quizzes)
                                            ├─ HeyGen API (avatars)
                                            ├─ Deepgram API (TTS)
                                            ├─ Cerebras/OpenAI (quiz generation)
                                            └─ SQLite DB

RTMS Service (Render) ←─── Zoom RTMS WebSocket ───→ Zoom Meeting
       │
       └── Real-time transcripts, audio, video, chat
```

## Current Status

✅ **Phase 1 Complete** - Foundation built
- Electron frontend with frosted glass UI
- Python FastAPI backend
- WebSocket communication
- SQLite database

✅ **Phase 2 Complete** - Zoom Integration
- Zoom API adapter
- Meeting and breakout room creation
- SessionOrchestrator service

✅ **Phase 3 Complete** - HeyGen Avatar Integration
- HeyGen Streaming Avatar SDK
- Real-time lip-sync with audio
- Avatar window for student tutoring

✅ **Quiz Bot Complete** - Interactive Quiz System
- Zoom Team Chat Chatbot integration
- Auto-generated quizzes from lecture concepts
- Video explanations for wrong answers (Manim 3Blue1Brown style)
- Professor dashboard with quiz trigger button
- WebSocket architecture: Render receives webhooks, broadcasts to local Python

✅ **Manim Pipeline Complete** - Educational Video Generation
- YouTube lecture → Transcription → Scene splitting
- LLM-generated Manim animation code
- Voice cloning with PocketTTS
- Auto-linked quiz questions per video scene

See **[PLAN.md](./PLAN.md)** for full roadmap.

## Manim Video Pipeline

Generate 3Blue1Brown-style animated videos from any YouTube lecture:

```bash
# Set up environment
export DEDALUS_API_KEY="your-key"
export HF_TOKEN="your-huggingface-token"

# Generate videos from a YouTube lecture
uv run python -c "
import asyncio
from src.pipeline import run

asyncio.run(run(
    'https://www.youtube.com/watch?v=VIDEO_ID',
    'outputs/topic-name',
    clip_concurrency=4
))
"
```

**Pipeline stages:**
1. Download audio from YouTube
2. Transcribe with Whisper (via Dedalus API)
3. LLM splits into concept-based scenes
4. Generate Manim animation code per scene
5. Clone speaker's voice (PocketTTS)
6. Render animations with voiceover
7. Stitch into final video

**Output:**
- `outputs/topic-name/videos/final.mp4` - Complete video
- `outputs/topic-name/videos/scene_XXX_voiced.mp4` - Individual scenes
- `outputs/topic-name/quiz_questions.json` - Auto-linked quiz

See **[docs/QUIZ_INTEGRATION.md](./docs/QUIZ_INTEGRATION.md)** for full integration guide.

## Quick Start

```bash
# 1. Install dependencies
npm install
cd backend && pip install -r requirements.txt

# 2. Configure environment
cd backend
cp .env.example .env
# Add your API keys to .env

# 3. Initialize database
python scripts/init_db.py
python scripts/seed_data.py

# 4. Run the app
npm run dev
```

See [docs/QUICKSTART.md](./docs/QUICKSTART.md) for detailed setup instructions.

## Tech Stack

- **Frontend**: Electron, React, TypeScript, Tailwind CSS
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **RTMS Service**: Node.js, Express (handles Zoom real-time media streams)
- **Database**: SQLite (development), PostgreSQL (production)
- **APIs**:
  - Zoom REST API (meetings, users)
  - Zoom Team Chat Chatbot API (interactive quizzes)
  - Zoom RTMS (real-time transcripts)
  - HeyGen Streaming Avatar SDK
  - Deepgram (speech-to-text, text-to-speech)
  - Cerebras/OpenAI (quiz generation)
- **Deployment**: Render (RTMS service + backend), Electron packaged app (frontend)

## Documentation

- [PLAN.md](./PLAN.md) - Project roadmap and status
- [docs/QUICKSTART.md](./docs/QUICKSTART.md) - Quick start guide
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Deployment instructions
- [docs/API.md](./docs/API.md) - API documentation
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System architecture
- [docs/QUIZ_INTEGRATION.md](./docs/QUIZ_INTEGRATION.md) - Manim video + quiz integration guide

## License

MIT

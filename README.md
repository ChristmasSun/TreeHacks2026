# AI Professor Clone Breakout Room System

> Automated Zoom breakout rooms with HeyGen AI professor clones for personalized student support

[![Phase 1](https://img.shields.io/badge/Phase%201-Complete-success)]()
[![Phase 2](https://img.shields.io/badge/Phase%202-Complete-success)]()
[![Phase 3](https://img.shields.io/badge/Phase%203-Pending-yellow)]()

## Quick Links

- **[📋 Project Plan](./PLAN.md)** - Complete project roadmap and status
- **[🚀 Quick Start Guide](./docs/QUICKSTART.md)** - Get started in 5 minutes
- **[📚 Full Documentation](./docs/README.md)** - Complete documentation
- **[🔧 Deployment Guide](./docs/DEPLOYMENT.md)** - Deploy to Render

## What is This?

An educational tool that uses AI to provide personalized 1-on-1 support to students at scale. When a professor starts a session:

1. **Automatic Breakout Rooms** - Creates Zoom breakout rooms for each student
2. **AI Professor Clones** - HeyGen avatars join each room to help students
3. **Smart Conversations** - Real-time transcription and context-aware responses
4. **Analytics Dashboard** - Track confusion points and student progress

## Architecture

```
Electron UI (Top Bar) ←→ WebSocket ←→ Python Backend (Render)
                                            ├─ Zoom API
                                            ├─ HeyGen API
                                            ├─ Deepgram API
                                            └─ SQLite DB
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

🔄 **Next: Phase 3** - HeyGen Avatar Integration

See **[PLAN.md](./PLAN.md)** for full roadmap.

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
- **Database**: SQLite (development), PostgreSQL (production)
- **APIs**: Zoom, HeyGen, Deepgram
- **Deployment**: Render (backend), Electron packaged app (frontend)

## Documentation

- [PLAN.md](./PLAN.md) - Project roadmap and status
- [docs/QUICKSTART.md](./docs/QUICKSTART.md) - Quick start guide
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Deployment instructions
- [docs/API.md](./docs/API.md) - API documentation
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) - System architecture

## License

MIT

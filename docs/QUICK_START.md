# Quick Start Guide

Complete guide to running the AI Professor Breakout Room system locally.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for Zoom Bot Service)
- **npm or yarn**
- **PostgreSQL** (optional, defaults to SQLite)

## API Keys Required

### 1. Zoom Credentials

You need **TWO** different sets of Zoom credentials:

#### Zoom REST API (for managing meetings/breakout rooms)
- Create Server-to-Server OAuth app: https://marketplace.zoom.us/
- Copy: Account ID, Client ID, Client Secret

#### Zoom Meeting SDK (for bots joining meetings)
- Create Meeting SDK app: https://marketplace.zoom.us/
- Copy: SDK Key, SDK Secret
- ⚠️ **These are different from REST API credentials!**

### 2. HeyGen API Key
- Sign up: https://app.heygen.com/
- Get API key from account settings
- Create an Interactive Avatar (note the avatar_id)

### 3. Deepgram API Key
- Sign up: https://deepgram.com/
- Create API key from dashboard

## Installation

### 1. Clone & Setup Python Backend

```bash
cd /path/to/TreeHacks2026

# Install Python dependencies
pip install -r backend/requirements.txt

# Create .env file
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```bash
# Database
DATABASE_URL=sqlite:///./database.db  # or PostgreSQL URL for production

# Zoom REST API
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret

# HeyGen
HEYGEN_API_KEY=your_heygen_api_key

# Deepgram
DEEPGRAM_API_KEY=your_deepgram_api_key

# Bot Service
ZOOM_BOT_SERVICE_URL=http://localhost:3001
```

### 2. Setup Zoom Bot Service

```bash
cd zoom-bot-service

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

Edit `zoom-bot-service/.env`:
```bash
# Zoom Meeting SDK (NOT REST API credentials!)
ZOOM_SDK_KEY=your_sdk_key
ZOOM_SDK_SECRET=your_sdk_secret

# Service config
PORT=3001
PYTHON_BACKEND_URL=http://localhost:8000
```

### 3. Setup Electron Frontend

```bash
cd /path/to/TreeHacks2026

# Install dependencies
npm install
```

## Running the System

You need **THREE** terminals:

### Terminal 1: Zoom Bot Service
```bash
cd zoom-bot-service
npm run dev
```

Should output:
```
✓ Zoom Bot Service running on port 3001
```

### Terminal 2: Python Backend
```bash
cd backend

# Initialize database (first time only)
python -c "from models.database import init_db; import asyncio; asyncio.run(init_db())"

# Seed test data (optional)
python scripts/seed_data.py

# Run backend
uvicorn app:app --reload --port 8000
```

Should output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 3: Electron Frontend
```bash
npm run dev
```

Should launch Electron window with frosted glass top bar.

## Testing the Setup

### 1. Check Services Health

```bash
# Bot service
curl http://localhost:3001/health

# Python backend
curl http://localhost:8000/health
```

### 2. Validate API Credentials

In Electron UI:
- Click "Validate Zoom" - should show ✅
- Check browser console for HeyGen/Deepgram validation

### 3. Create Test Session

1. In Electron UI, click **"Start Session"**
2. Backend will:
   - Create Zoom meeting with breakout rooms
   - Deploy HeyGen avatars (one per student)
   - Create Zoom bots to join meeting
   - Start transcription streams

3. Monitor progress in UI dashboard

## Architecture Flow

```
┌─────────────────────────┐
│ Electron Frontend       │ (Port: varies)
│ - Professor controls    │
└───────────┬─────────────┘
            │ WebSocket
┌───────────▼─────────────┐
│ Python Backend (FastAPI)│ (Port: 8000)
│ - Session orchestration │
│ - Zoom REST API         │
│ - HeyGen API            │
│ - Deepgram API          │
└───────┬─────────┬───────┘
        │         │
        │         └─────────────────┐
        │                           │
┌───────▼─────────────┐   ┌────────▼──────────┐
│ Zoom Bot Service    │   │ External APIs     │
│ (Node.js + Rivet)   │   │ - Zoom            │
│ - Bots join meeting │   │ - HeyGen          │
│ - Audio routing     │   │ - Deepgram        │
└─────────────────────┘   └───────────────────┘
```

## Common Issues

### "Module not found" errors
```bash
# Python
pip install -r backend/requirements.txt

# Node.js
cd zoom-bot-service && npm install
cd .. && npm install
```

### Zoom SDK vs REST API confusion
- **REST API** = Account ID, Client ID, Client Secret (for creating meetings)
- **Meeting SDK** = SDK Key, SDK Secret (for bots joining meetings)
- You need BOTH sets of credentials!

### Bots not joining Zoom
- Check `zoom-bot-service` is running on port 3001
- Verify `ZOOM_SDK_KEY` and `ZOOM_SDK_SECRET` in `zoom-bot-service/.env`
- Check bot service logs for Rivet SDK errors

### HeyGen avatars not created
- Verify `HEYGEN_API_KEY` in `backend/.env`
- Check you have an Interactive Avatar created in HeyGen dashboard
- Update `backend/scripts/seed_data.py` with your avatar_id

### Transcription not working
- Verify `DEEPGRAM_API_KEY` in `backend/.env`
- Check Deepgram account has credits
- Monitor browser console for WebSocket errors

## Next Steps

Once the system is running:

1. **Test with real Zoom meeting**
   - Start session in Electron UI
   - Join Zoom meeting as student
   - Interact with AI professor bot

2. **Upload course materials**
   - Use Context Engine to ingest PDFs, slides
   - Avatars will use this for contextual responses

3. **Review analytics**
   - After session ends, check analytics dashboard
   - View confusion points and topic coverage

## Development Tips

### Hot Reload
- Python backend: Uses `--reload` flag (auto-restarts on file changes)
- Node.js bot service: Uses `ts-node` with nodemon (auto-restarts)
- Electron frontend: Uses Vite HMR (hot module replacement)

### Debugging
- Python: Add breakpoints, run with `python -m pdb`
- Node.js: Use `console.log()` or attach debugger
- Electron: Open DevTools (View → Toggle Developer Tools)

### Database Inspection
```bash
# SQLite
sqlite3 backend/database.db
.tables
SELECT * FROM sessions;

# PostgreSQL
psql $DATABASE_URL
\dt
SELECT * FROM sessions;
```

## Production Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for deploying to Render.

## Support

- Issues: https://github.com/anthropics/claude-code/issues
- Zoom SDK Docs: https://developers.zoom.us/docs/video-sdk/
- HeyGen API: https://docs.heygen.com/
- Deepgram API: https://developers.deepgram.com/

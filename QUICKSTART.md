# Quick Start Guide

## Phase 1 Foundation ✅ COMPLETE

We've successfully built the foundation for the AI Professor Breakout Room System:

### What's Been Built

1. **Project Structure** ✅
   - Electron + Python architecture
   - TypeScript configuration
   - Tailwind CSS with frosted glass styling
   - Development workflow setup

2. **SQLite Database** ✅
   - Complete schema with 8 tables
   - SQLAlchemy ORM models
   - Database initialization scripts

3. **FastAPI Backend** ✅
   - WebSocket endpoint for real-time communication
   - REST API endpoints
   - Connection manager for multiple clients
   - Message routing system

4. **Electron Frontend** ✅
   - Minimal "frosted glass" top-bar UI (Cluely-style)
   - React + TypeScript
   - Dashboard with Start/End Session buttons
   - Window controls (minimize, close)

5. **WebSocket Communication** ✅
   - Bidirectional Electron ↔ Python messaging
   - Auto-reconnect functionality
   - IPC handlers for renderer ↔ main process

## Getting Started

### Prerequisites

Install these if you don't have them:
- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Python 3.11+** - [Download here](https://www.python.org/)

### Installation Steps

1. **Install frontend dependencies:**
   ```bash
   npm install
   ```

2. **Set up Python virtual environment:**
   ```bash
   cd backend
   python -m venv venv

   # On macOS/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database:**
   ```bash
   python scripts/init_db.py
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (you can leave them blank for now)
   ```

### Run the Application

**Option 1: Run everything together (recommended)**
```bash
npm run dev
```

**Option 2: Run separately in two terminals**

Terminal 1 (Backend):
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app:app --reload --port 8000
```

Terminal 2 (Frontend):
```bash
npm run dev:electron
```

### What You'll See

When you run the app, you'll see:
- A minimal frosted glass bar at the top of your screen
- Connection status indicator (should show "Connected" when backend is running)
- "Start Session" button to test the WebSocket communication
- "End Session" button when a session is active

### Testing the Connection

1. Start the app with `npm run dev`
2. The status indicator should turn green and say "Connected"
3. Click "Start Session" - check the terminal logs to see the WebSocket message flow
4. Check the backend terminal - you should see "Received message: CREATE_SESSION"
5. Click "End Session" to test ending a session

### Project Structure

```
TreeHacks2026/
├── src/electron/              # Electron frontend
│   ├── main/                  # Main process (Node.js)
│   │   ├── index.ts           # Window creation
│   │   ├── websocket-client.ts # WebSocket client
│   │   ├── ipc-handlers.ts    # IPC message routing
│   │   └── preload.ts         # Context bridge
│   └── renderer/              # Renderer process (React)
│       ├── components/        # React components
│       ├── App.tsx            # Main app
│       └── styles/            # CSS styles
├── backend/                   # Python backend
│   ├── app.py                 # FastAPI app
│   ├── models/                # Database models
│   ├── services/              # Business logic (TODO)
│   └── integrations/          # API adapters (TODO)
├── package.json               # Node dependencies
└── backend/requirements.txt   # Python dependencies
```

## Next Steps: Phase 2 - Zoom Integration

To continue development, we need to:

1. **Get Zoom API Credentials:**
   - Go to [Zoom Marketplace](https://marketplace.zoom.us/)
   - Create a Server-to-Server OAuth app
   - Get API Key, Secret, and Account ID
   - Add to `.env` file

2. **Implement ZoomManager service** (`backend/services/zoom_manager.py`)
   - Create meetings
   - Create breakout rooms
   - Assign participants

3. **Test with real Zoom meetings**
   - Create a test meeting
   - Programmatically create breakout rooms
   - Verify API integration works

## Troubleshooting

### "Cannot find module" errors
```bash
npm install
```

### Python import errors
```bash
cd backend
pip install -r requirements.txt
```

### WebSocket won't connect
- Make sure the backend is running on port 8000
- Check `backend/app.py` logs for errors
- Try `curl http://localhost:8000/health` to verify backend is up

### Electron window doesn't appear
- Check for errors in the terminal
- Try running `npm run dev:electron` separately
- On macOS, check if you've granted screen recording permissions

## Development Tips

- **Backend logs**: Watch the terminal running uvicorn for WebSocket messages
- **Frontend logs**: Open DevTools in the Electron window (uncomment line 35 in `src/electron/main/index.ts`)
- **Database inspection**: Use SQLite browser or run `sqlite3 backend/breakout_system.db`
- **Hot reload**: Both frontend and backend support hot reload during development

## API Keys Needed (for later phases)

You'll need these API credentials:
- ✅ Zoom API (OAuth app) - Phase 2
- ✅ HeyGen API (Interactive Avatar) - Phase 3
- ✅ Deepgram API (Transcription) - Phase 4

Don't worry about getting these now - the foundation works without them!

---

## Summary

✅ **Phase 1 (Foundation) - COMPLETE**
- Electron app with frosted glass UI
- Python FastAPI backend
- WebSocket communication
- SQLite database

🔜 **Phase 2 (Zoom Integration) - Next**
- Zoom API credentials
- ZoomManager service
- Breakout room creation

🔜 **Phase 3 (HeyGen Avatars) - Future**
- HeyGen API integration
- Avatar deployment

🔜 **Phase 4 (Transcription) - Future**
- Deepgram integration
- Real-time transcription

Ready to move forward? Let me know when you have your Zoom API credentials and we'll start Phase 2!

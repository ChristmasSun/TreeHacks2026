# AI Professor Clone Breakout Room System

An educational tool that automates Zoom breakout rooms with HeyGen AI clones of professors, enabling personalized 1-on-1 student support at scale.

## Features

- **Automated Breakout Rooms**: Automatically create and manage Zoom breakout rooms
- **AI Professor Clones**: HeyGen avatars join each room to help students
- **Real-Time Transcription**: Deepgram captures all student-bot conversations
- **Context-Aware AI**: RAG system gives bots access to course materials
- **Analytics Dashboard**: Track student progress, confusion points, and topic coverage

## Architecture

- **Frontend**: Electron app with minimal "frosted glass" UI (Cluely-style)
- **Backend**: Python FastAPI orchestrating Zoom, HeyGen, and Deepgram APIs
- **Database**: SQLite for session data and analytics
- **Communication**: WebSocket for real-time frontend ↔ backend messaging

## Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Zoom API credentials (OAuth app or Server-to-Server OAuth)
- HeyGen API access (Interactive Avatar feature)
- Deepgram API key

### Installation

1. **Install frontend dependencies:**
   ```bash
   npm install
   ```

2. **Install backend dependencies:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your API credentials
   ```

4. **Initialize database:**
   ```bash
   cd backend
   python -m scripts.init_db
   ```

### Development

Run both Electron frontend and Python backend simultaneously:

```bash
npm run dev
```

Or run them separately:

```bash
# Terminal 1: Backend
npm run dev:backend

# Terminal 2: Frontend
npm run dev:electron
```

### Build

```bash
npm run build
npm run build:electron
```

## Project Structure

```
.
├── src/
│   └── electron/
│       ├── main/              # Electron main process
│       │   ├── index.ts       # Entry point
│       │   ├── websocket-client.ts
│       │   └── preload.ts     # Context bridge
│       └── renderer/          # Electron renderer (React UI)
│           ├── components/    # React components
│           ├── services/      # API clients
│           └── store/         # State management
├── backend/
│   ├── app.py                 # FastAPI entry point
│   ├── services/              # Core services
│   │   ├── session_orchestrator.py
│   │   ├── zoom_manager.py
│   │   ├── heygen_controller.py
│   │   ├── transcription_service.py
│   │   ├── context_engine.py
│   │   └── analytics_generator.py
│   ├── models/                # Database models
│   ├── integrations/          # API adapters
│   └── tests/                 # Backend tests
└── package.json
```

## Usage

1. **Start the application**: `npm run dev`
2. **Configure session**: Click settings to upload course materials
3. **Start breakout session**: Click "Start Session" button
4. **Monitor rooms**: View real-time status of all breakout rooms
5. **End session**: Click "End Session" to close rooms and generate analytics
6. **Review analytics**: View student progress, confusion points, and recommendations

## API Integration

### Zoom API
- Create meetings and breakout rooms
- Assign participants to rooms
- Capture audio streams for transcription

### HeyGen API
- Create Interactive Avatar sessions
- Configure avatar with professor profile
- Join Zoom rooms as participants

### Deepgram API
- Real-time audio transcription via WebSocket
- Speaker diarization (student vs bot)
- High-accuracy transcripts for analytics

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
npm test
```

## License

MIT

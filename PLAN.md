# Project Plan: AI Professor Clone Breakout Room System

## Overview

An educational platform that provides personalized 1-on-1 support to students at scale using AI-powered professor clones in Zoom breakout rooms.

## Services & APIs

### External Services
| Service | Purpose | Status | Cost |
|---------|---------|--------|------|
| **Zoom API** | Meeting & breakout room management | ✅ Integrated | Free tier available |
| **HeyGen Interactive Avatar** | AI professor video clones | 🔄 Pending | ~$0.03/min per avatar |
| **Deepgram** | Real-time audio transcription | 🔄 Pending | $0.0043/min |
| **Render** | Backend hosting | 🔄 Setting up | Free tier available |

### Internal Services
| Service | Technology | Status |
|---------|-----------|--------|
| **Frontend** | Electron + React + TypeScript | ✅ Complete |
| **Backend** | Python FastAPI | ✅ Complete |
| **Database** | SQLite (dev) / PostgreSQL (prod) | ✅ Complete |
| **WebSocket** | FastAPI WebSockets | ✅ Complete |

## Project Phases

### ✅ Phase 1: Foundation (COMPLETE)

**Goal**: Build the core architecture and communication layer

**Completed Tasks**:
1. ✅ Project structure setup
   - Electron + Python architecture
   - TypeScript configuration
   - Tailwind CSS with frosted glass UI
   - Development workflow

2. ✅ Database schema
   - 8 tables: sessions, breakout_rooms, transcripts, student_progress, professors, students, context_documents, session_analytics
   - SQLAlchemy ORM models
   - Database initialization scripts

3. ✅ FastAPI backend
   - WebSocket endpoint for real-time communication
   - REST API endpoints
   - Connection manager
   - Message routing system

4. ✅ Electron frontend
   - Minimal "frosted glass" top-bar UI (Cluely-style)
   - React components with TypeScript
   - Dashboard with session controls
   - Window management

5. ✅ WebSocket communication
   - Bidirectional Electron ↔ Python messaging
   - Auto-reconnect functionality
   - IPC handlers

**Files Created**: 25+ files across frontend, backend, and configuration

---

### ✅ Phase 2: Zoom Integration (COMPLETE)

**Goal**: Integrate Zoom API for meeting and breakout room management

**Completed Tasks**:
1. ✅ Zoom API Adapter (`backend/integrations/zoom_sdk_adapter.py`)
   - Server-to-Server OAuth authentication
   - Meeting creation/management
   - Breakout room creation/assignment
   - Participant management
   - Error handling and retries

2. ✅ ZoomManager Service (`backend/services/zoom_manager.py`)
   - High-level meeting operations
   - Breakout room orchestration
   - One-student-per-room assignments
   - Meeting URL generation

3. ✅ SessionOrchestrator (`backend/services/session_orchestrator.py`)
   - Complete session lifecycle management
   - Coordinates Zoom + future services (HeyGen, Deepgram)
   - Database integration
   - Session monitoring

4. ✅ Updated Dashboard UI
   - Zoom credentials validation
   - Session creation with real Zoom meetings
   - Copy meeting URL to clipboard
   - Session status indicators

**Files Created**: 5 new service files + updated app.py and Dashboard.tsx

**Current Capabilities**:
- ✅ Create Zoom meetings programmatically
- ✅ Create breakout rooms (one per student)
- ✅ Pre-assign students to rooms
- ✅ Track session status in database
- ⚠️ Opening/closing rooms requires manual host action or SDK bot (Phase 3.5)

---

### 🔄 Phase 3: HeyGen Avatar Integration (NEXT - 40% complete architecture)

**Goal**: Deploy HeyGen AI avatars to join Zoom breakout rooms

**Remaining Tasks**:
1. 🔄 HeyGen API Adapter (`backend/integrations/heygen_api_adapter.py`)
   - Interactive Avatar API v2 integration
   - Streaming avatar session management
   - WebRTC connection handling

2. 🔄 HeyGenController Service (`backend/services/heygen_controller.py`)
   - Create avatar sessions with professor profile
   - Join Zoom meetings as participants
   - Context injection for course materials
   - Avatar lifecycle management

3. 🔄 Zoom + HeyGen Integration
   - Generate Zoom participant credentials for avatars
   - Avatar joins specific breakout room
   - Audio/video stream setup
   - Handle avatar disconnections

4. 🔄 Update SessionOrchestrator
   - Deploy avatars after breakout rooms created
   - Track avatar session IDs in database
   - Disconnect avatars on session end

5. 🔄 Update Dashboard UI
   - Show avatar status per room (connected/disconnected/error)
   - Manual avatar restart controls
   - Avatar health monitoring

**Estimated Time**: 3-4 days

**Technical Challenge**: HeyGen avatars joining Zoom as participants
- **Solution**: Use Zoom SDK to create virtual participants with HeyGen video/audio streams

---

### 🔄 Phase 4: Real-Time Transcription (Pending)

**Goal**: Capture and transcribe all student-bot conversations

**Remaining Tasks**:
1. 🔄 Deepgram API Adapter (`backend/integrations/deepgram_adapter.py`)
   - WebSocket streaming API
   - Real-time transcription
   - Speaker diarization (student vs bot)

2. 🔄 TranscriptionService (`backend/services/transcription_service.py`)
   - Connect to Zoom room audio streams
   - Stream to Deepgram
   - Save transcripts to database
   - Real-time transcript forwarding to frontend

3. 🔄 Zoom Audio Routing
   - Capture room audio via Zoom SDK
   - Fork stream to Deepgram + HeyGen
   - Handle audio sync issues

4. 🔄 Database Integration
   - Save transcripts with timestamps
   - Link to breakout_rooms table
   - Enable post-session analysis

5. 🔄 Update SessionMonitor UI
   - Live transcript view per room
   - Searchable conversation history
   - Export transcripts

**Estimated Time**: 2-3 days

---

### 🔄 Phase 5: Context Engine (RAG System) (Pending)

**Goal**: Give avatars access to professor's course materials for context-aware responses

**Remaining Tasks**:
1. 🔄 Context Engine (`backend/services/context_engine.py`)
   - Document ingestion (PDF, PPTX, Markdown, TXT)
   - Text extraction and chunking
   - Vector embeddings (sentence-transformers)
   - ChromaDB integration

2. 🔄 Vector Database Setup
   - ChromaDB or Pinecone configuration
   - Embedding storage per professor
   - Semantic search implementation

3. 🔄 Context Retrieval
   - Query vector DB based on student questions
   - Return relevant lecture content
   - Inject into HeyGen avatar prompts

4. 🔄 Document Management UI
   - Upload course materials (Frontend)
   - View/delete uploaded documents
   - Tag documents by topic/lecture

5. 🔄 Integration with HeyGen
   - Pre-load context when avatar starts
   - Real-time context injection during conversation
   - Context relevance scoring

**Estimated Time**: 3-4 days

---

### 🔄 Phase 6: Analytics & Monitoring (Pending)

**Goal**: Provide real-time insights and post-session analytics

**Remaining Tasks**:
1. 🔄 Real-Time Monitoring
   - SessionMonitor component (Frontend)
   - Live room status grid (30+ rooms)
   - Confusion detection (repeated questions)
   - Idle room detection (no conversation)
   - Intervention alerts

2. 🔄 Analytics Generator (`backend/services/analytics_generator.py`)
   - Post-session summary generation
   - Confusion point identification
   - Topic coverage matrix
   - Engagement scoring
   - Student progress tracking

3. 🔄 Analytics UI
   - AnalyticsSummary component
   - Confusion heatmap visualization
   - Student progress reports
   - Recommended follow-up actions

4. 🔄 Database Analytics
   - SessionAnalytics table population
   - StudentProgress updates
   - Historical trend analysis

**Estimated Time**: 3-4 days

---

### 🔄 Phase 7: Deployment & Production (In Progress)

**Goal**: Deploy backend to Render and package Electron app

**Remaining Tasks**:
1. 🔄 Render Backend Deployment
   - Create `render.yaml` configuration
   - PostgreSQL database setup on Render
   - Environment variable configuration
   - Health check endpoints
   - Production logging

2. 🔄 Database Migration
   - Switch from SQLite to PostgreSQL
   - Alembic migrations setup
   - Production schema deployment

3. 🔄 Electron App Packaging
   - electron-builder configuration
   - Code signing (macOS/Windows)
   - Auto-update mechanism
   - Production build optimization

4. 🔄 Security & Performance
   - API rate limiting
   - CORS configuration for production
   - WebSocket connection limits
   - Error monitoring (Sentry?)

5. 🔄 CI/CD Pipeline
   - GitHub Actions for backend deployment
   - Automated testing
   - Frontend build pipeline

**Estimated Time**: 2-3 days

---

### 🔄 Phase 8: Testing & Polish (Pending)

**Goal**: Comprehensive testing and UX improvements

**Remaining Tasks**:
1. 🔄 End-to-End Testing
   - Test full session with 5+ students
   - Verify avatars join correctly
   - Test transcription accuracy
   - Validate analytics generation

2. 🔄 Load Testing
   - 30 concurrent breakout rooms
   - Multiple simultaneous sessions
   - Backend performance benchmarking

3. 🔄 Error Handling
   - Network disconnection recovery
   - API failure fallbacks
   - User-friendly error messages
   - Automatic retry mechanisms

4. 🔄 UX Improvements
   - Onboarding flow for first-time users
   - Keyboard shortcuts
   - Settings panel
   - Help documentation

5. 🔄 Documentation
   - User manual
   - API documentation
   - Troubleshooting guide
   - Video tutorials

**Estimated Time**: 2-3 days

---

## Feature Roadmap (Future Phases)

### Feature #1: Live Confusion Detection
- Analyze camera feeds to detect confused students
- Auto-trigger breakout sessions when multiple students look confused
- Integration with existing system

### Feature #3: Auto-Quiz Generation
- Generate quizzes from session transcripts
- Create Manim (3Blue1Brown style) videos for missed questions
- Track quiz performance per student

## Timeline Summary

| Phase | Status | Duration | Completion Date |
|-------|--------|----------|-----------------|
| Phase 1: Foundation | ✅ Complete | 3 days | Feb 14, 2026 |
| Phase 2: Zoom Integration | ✅ Complete | 1 day | Feb 14, 2026 |
| Phase 3: HeyGen Avatars | 🔄 Next | 3-4 days | TBD |
| Phase 4: Transcription | 🔄 Pending | 2-3 days | TBD |
| Phase 5: Context Engine | 🔄 Pending | 3-4 days | TBD |
| Phase 6: Analytics | 🔄 Pending | 3-4 days | TBD |
| Phase 7: Deployment | 🔄 In Progress | 2-3 days | TBD |
| Phase 8: Testing & Polish | 🔄 Pending | 2-3 days | TBD |

**Total Estimated Time**: 20-28 days (3-4 weeks)

---

## Critical Dependencies

### API Credentials Needed

✅ **Zoom API**
- Account ID
- Client ID
- Client Secret
- Status: Ready to configure

🔄 **HeyGen API**
- API Key
- Interactive Avatar access
- Status: Need to obtain

🔄 **Deepgram API**
- API Key
- Status: Need to obtain

✅ **Render**
- Account created
- Status: Ready to deploy

### Technical Challenges

1. **HeyGen → Zoom Integration** (Phase 3)
   - Challenge: HeyGen doesn't natively join Zoom rooms
   - Solution: Use Zoom SDK to create virtual participants

2. **Real-Time Audio Routing** (Phase 4)
   - Challenge: Student → Zoom → Deepgram → HeyGen → Student latency
   - Solution: Parallel processing architecture

3. **Scaling HeyGen Avatars** (Phase 3)
   - Challenge: Cost at 30+ concurrent avatars
   - Solution: Avatar pooling, hybrid approach for struggling students

4. **Opening Breakout Rooms** (Phase 2.5)
   - Challenge: Zoom API can't auto-open rooms
   - Solution: Headless Zoom SDK bot as co-host OR manual host action

---

## Success Metrics

- ✅ Professor can start session in <30 seconds
- 🔄 HeyGen avatars join rooms with >95% success rate
- 🔄 Transcription accuracy >90% (WER)
- 🔄 Avatar response latency <2 seconds
- 🔄 Analytics generated within 10 seconds of session end
- 🔄 UI remains responsive during 30 concurrent rooms

---

## Next Immediate Steps

1. **Deploy Backend to Render** (Current)
   - Create `render.yaml`
   - Set up PostgreSQL
   - Deploy and test

2. **Get API Credentials**
   - HeyGen API access
   - Deepgram API key

3. **Start Phase 3: HeyGen Integration**
   - Build HeyGenController
   - Test avatar joining Zoom
   - Integrate with SessionOrchestrator

---

*Last Updated: Feb 14, 2026*

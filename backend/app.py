"""
FastAPI application with WebSocket support for Electron frontend
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import asyncio
import json
import logging
import os
from datetime import datetime
from urllib.parse import urlencode

from models import get_db, init_db
from models.models import Professor, Student, Session, BreakoutRoom
from services.session_orchestrator import SessionOrchestrator
from services.llm_service import (
    generate_tutoring_response,
    set_lecture_context,
    get_lecture_context,
    set_lecture_transcript,
    get_lecture_transcript,
    set_active_meeting,
    get_active_meeting,
    fetch_rtms_transcripts,
)
from services.tts_service import text_to_speech
from services.rtms_transcription_service import RTMSTranscriptionService
from services.pocket_tts_service import PocketTTSService
from services.tutor_session import TutorSession, SessionState
from services.heygen_controller import HeyGenController
from services.zoom_chatbot_service import (
    verify_webhook_signature,
    generate_url_validation_response,
    send_quiz_intro,
    parse_answer_value,
    get_user_jid,
)
from services.quiz_generator import (
    generate_quiz_from_concepts,
    generate_quiz_from_output_dir,
    load_concept_video_mapping,
)
from services.quiz_session_manager import (
    get_session as get_quiz_session,
    create_session as create_quiz_session,
    start_quiz,
    handle_answer,
    handle_video_completed,
    cancel_quiz,
    get_session_stats,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Professor Breakout System",
    description="Backend API for automated breakout rooms with HeyGen AI clones",
    version="1.0.0"
)

# CORS middleware for Electron frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections to Electron clients"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, websocket: WebSocket, message: dict):
        """Send message to specific client"""
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


manager = ConnectionManager()

# Initialize services
rtms_service = RTMSTranscriptionService()
heygen_controller = HeyGenController()
pocket_tts_service = PocketTTSService()


# Transcript callback for real-time forwarding to frontend
async def forward_transcript_to_frontend(transcript_data: dict):
    """Forward real-time transcripts to all connected frontend clients"""
    await manager.broadcast({
        "type": "TRANSCRIPT_UPDATE",
        "payload": transcript_data
    })


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and ML models on startup"""
    logger.info("Starting up application...")
    await init_db()
    logger.info("Database initialized")

    # Pre-load Pocket TTS model for low-latency generation
    try:
        pocket_tts_service.load()
    except Exception as e:
        logger.error(f"Failed to load Pocket TTS: {e}")

    # Start Render WebSocket client for video frames
    try:
        from services.render_ws_client import register_handler, start_render_client
        from services.chatbot_ws_handler import setup_chatbot_handlers
        import asyncio
        import base64

        # Register video frame handler
        async def handle_video_frame(event: dict):
            """Process video frames from RTMS via Render WebSocket."""
            data = event.get("data", {})
            user_id = data.get("user_id", "unknown")
            user_name = data.get("user_name", "Unknown")
            frame_b64 = data.get("frame_base64", "")

            if not frame_b64:
                return

            try:
                frame_bytes = base64.b64decode(frame_b64)
                logger.info(f"[Video] Processing frame from {user_name} ({len(frame_bytes)} bytes)")

                # Run FER analysis
                metrics = await demeanor_service.analyze_frame(user_id, user_name, frame_bytes)

                # Broadcast to frontend
                logger.info(f"[Video] Broadcasting to {len(manager.active_connections)} clients")
                await manager.broadcast({
                    "type": "DEMEANOR_UPDATE",
                    "payload": {
                        "user_id": user_id,
                        "user_name": user_name,
                        "engagement_score": metrics.engagement_score,
                        "attention": metrics.attention,
                        "expression": metrics.expression,
                        "timestamp": metrics.timestamp,
                    }
                })
                logger.info(f"[Video] {user_name}: {metrics.expression}, engagement={metrics.engagement_score}")
            except Exception as e:
                logger.error(f"[Video] Frame processing error: {e}")

        register_handler("video_frame", handle_video_frame)
        setup_chatbot_handlers()
        logger.info("Registered video_frame and chatbot handlers")

        # Start Render WebSocket client in background
        render_url = os.getenv("RENDER_WS_URL", "wss://rtms-webhook.onrender.com/ws")
        asyncio.create_task(start_render_client(render_url))
        logger.info(f"Started Render WebSocket client: {render_url}")
    except Exception as e:
        logger.error(f"Failed to start Render WebSocket client: {e}")


# Mount static files for audio and videos
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(static_dir, "audio"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "videos"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": len(manager.active_connections)
    }


# OAuth callback for Zoom app installation
@app.get("/oauth/callback")
async def oauth_callback(code: str = None, error: str = None):
    """
    Handle OAuth callback from Zoom app installation.
    For chatbot apps, we just need to acknowledge the installation.
    """
    if error:
        return HTMLResponse(f"""
        <html>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>Installation Failed</h1>
                <p>Error: {error}</p>
                <p>Please try again or contact support.</p>
            </body>
        </html>
        """, status_code=400)

    if code:
        # For chatbot, we don't need to exchange the code for user tokens
        # The client_credentials flow handles bot authentication
        logger.info(f"Zoom app installed successfully (auth code received)")

    return HTMLResponse("""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>Quiz Bot Installed Successfully!</h1>
            <p>The quiz bot has been added to your Zoom account.</p>
            <p>You can now use <code>/quiz</code> in any Zoom Team Chat to start a quiz.</p>
            <p>You can close this window.</p>
        </body>
    </html>
    """)


# Professor Dashboard
@app.get("/dashboard")
async def professor_dashboard():
    """Serve professor dashboard"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "professor-dashboard.html")
    return FileResponse(dashboard_path, media_type="text/html")


# Lecture Context Endpoints
@app.get("/api/lecture-context")
async def get_context():
    """Get current lecture context"""
    return {"context": get_lecture_context()}

@app.post("/api/lecture-context")
async def set_context(data: dict):
    """Set lecture context for tutoring sessions"""
    topic = data.get("topic", "")
    key_points = data.get("key_points", "")
    notes = data.get("notes", "")
    set_lecture_context(topic, key_points, notes)
    logger.info(f"Lecture context updated: {topic}")
    return {"success": True, "context": get_lecture_context()}


# ============ Lecture Content Loading ============

@app.post("/api/lecture/load")
async def load_lecture_content(data: dict):
    """
    Load pre-processed pipeline output (transcript, concepts, videos).
    Called by professor to set up content for the session.
    """
    from pathlib import Path
    import shutil

    output_dir = data.get("output_dir", "")
    if not output_dir:
        raise HTTPException(status_code=400, detail="Missing output_dir")

    output_path = Path(output_dir)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {output_dir}")

    # 1. Load transcript
    transcript_path = output_path / "transcript.txt"
    transcript_length = 0
    if transcript_path.exists():
        transcript_text = transcript_path.read_text(encoding="utf-8")
        set_lecture_transcript(transcript_text)
        transcript_length = len(transcript_text)
        logger.info(f"Loaded transcript: {transcript_length} chars")

    # 2. Load concepts via existing mapping utility
    mapping = load_concept_video_mapping(output_dir)
    concepts_count = len(mapping)

    # 3. Copy videos to static directory
    global quiz_video_output_dir
    quiz_video_output_dir = output_dir

    videos_static_dir = Path(static_dir) / "videos"
    os.makedirs(videos_static_dir, exist_ok=True)
    videos_count = 0

    for concept, info in mapping.items():
        video_path = info.get("video_path")
        if video_path and Path(video_path).exists():
            video_filename = Path(video_path).name
            dest_path = videos_static_dir / video_filename
            if not dest_path.exists():
                shutil.copy2(video_path, dest_path)
            videos_count += 1

    # 4. Set lecture context from directory name
    topic = output_path.name.replace("-", " ").replace("_", " ").title()
    set_lecture_context(topic=topic, key_points=f"{concepts_count} concepts loaded", notes=output_dir)

    logger.info(f"Lecture loaded: {topic} ({concepts_count} concepts, {videos_count} videos)")

    return {
        "success": True,
        "topic": topic,
        "transcript_length": transcript_length,
        "concepts_count": concepts_count,
        "videos_count": videos_count,
        "output_dir": output_dir,
    }


@app.get("/api/lecture/status")
async def lecture_status():
    """Get current lecture loading state."""
    from pathlib import Path

    transcript = get_lecture_transcript()
    mapping = load_concept_video_mapping(quiz_video_output_dir) if quiz_video_output_dir else {}

    videos_dir = Path(static_dir) / "videos"
    video_count = len(list(videos_dir.glob("*.mp4"))) if videos_dir.exists() else 0

    return {
        "transcript_loaded": len(transcript) > 0,
        "transcript_length": len(transcript),
        "concepts_count": len(mapping),
        "videos_count": video_count,
        "output_dir": quiz_video_output_dir,
        "context": get_lecture_context(),
    }


@app.get("/api/server-info")
async def server_info():
    """Return server LAN IP and port for student connection."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"

    return {
        "server_ip": ip,
        "port": 8000,
        "ws_url": f"ws://{ip}:8000/ws",
        "api_url": f"http://{ip}:8000",
    }


# Tutor Response Endpoint
@app.post("/api/tutor-response")
async def get_tutor_response(data: dict):
    """Get LLM tutoring response for student question with live meeting context"""
    student_message = data.get("message", "")
    student_name = data.get("student_name", "Student")
    history = data.get("history", [])
    meeting_id = data.get("meeting_id")  # Optional - will auto-detect if not provided
    was_interrupted = data.get("was_interrupted", False)  # True if student interrupted avatar

    response = await generate_tutoring_response(
        student_message=student_message,
        student_name=student_name,
        conversation_history=history,
        meeting_id=meeting_id,
        was_interrupted=was_interrupted
    )
    return {"response": response}


# Set active meeting for transcript context
@app.post("/api/active-meeting")
async def set_meeting(data: dict):
    """Set the active meeting ID for transcript context"""
    meeting_id = data.get("meeting_id")
    if meeting_id:
        set_active_meeting(meeting_id)
        return {"success": True, "meeting_id": meeting_id}
    return {"success": False, "error": "No meeting_id provided"}


@app.get("/api/active-meeting")
async def get_meeting():
    """Get the active meeting ID"""
    meeting_id = get_active_meeting()
    return {"meeting_id": meeting_id}


# Get live transcript context
@app.get("/api/transcript-context")
async def get_transcript_context(meeting_id: str = None):
    """Get formatted transcript context from RTMS service"""
    context = await fetch_rtms_transcripts(meeting_id)
    return {
        "meeting_id": meeting_id or get_active_meeting(),
        "context": context,
        "length": len(context) if context else 0
    }


# Tutor Response with Audio (LLM + TTS pipeline)
@app.post("/api/tutor-audio")
async def get_tutor_audio(data: dict):
    """
    Full pipeline: LLM generates text -> TTS generates audio
    Returns both text and audio URL for HeyGen lip-sync
    """
    student_message = data.get("message", "")
    student_name = data.get("student_name", "Student")
    history = data.get("history", [])
    tts_provider = data.get("tts_provider", "openai")  # "openai" or "elevenlabs"
    voice_id = data.get("voice_id", None)  # Optional voice ID
    
    # Step 1: Generate text response
    text_response = await generate_tutoring_response(
        student_message=student_message,
        student_name=student_name,
        conversation_history=history
    )
    
    # Step 2: Convert to audio
    try:
        audio_result = await text_to_speech(
            text=text_response,
            voice_id=voice_id,
            provider=tts_provider
        )
        
        return {
            "response": text_response,
            "audio_url": audio_result["audio_url"],
            "audio_base64": audio_result["audio_base64"],
            "content_type": audio_result["content_type"]
        }
    except Exception as e:
        logger.error(f"TTS error: {e}")
        # Return text-only if TTS fails
        return {
            "response": text_response,
            "audio_url": None,
            "error": str(e)
        }


# HeyGen access token endpoint for frontend SDK
@app.get("/api/heygen-token")
async def get_heygen_token():
    """Generate HeyGen access token for frontend SDK"""
    import httpx
    import os
    
    api_key = os.getenv("HEYGEN_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="HeyGen API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.heygen.com/v1/streaming.create_token",
                headers={"X-Api-Key": api_key}
            )
            response.raise_for_status()
            data = response.json()
            return {"token": data.get("data", {}).get("token")}
    except Exception as e:
        logger.error(f"Failed to get HeyGen token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Audio Pipeline WebSocket ============

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")


async def connect_deepgram():
    """Connect to Deepgram nova-3 for backend-side STT."""
    import websockets

    params = urlencode({
        "model": "nova-3",
        "language": "en-US",
        "smart_format": "true",
        "interim_results": "true",
        "punctuate": "true",
        "encoding": "linear16",
        "sample_rate": "16000",
        "channels": "1",
    })
    url = f"wss://api.deepgram.com/v1/listen?{params}"
    ws = await websockets.connect(
        url, additional_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    )
    logger.info("Connected to Deepgram nova-3")
    return ws


async def deepgram_reader(dg_ws, session: TutorSession):
    """Read Deepgram transcript messages and forward to session."""
    import sys
    print("[Deepgram] Reader started, waiting for transcripts...", file=sys.stderr, flush=True)
    try:
        async for msg in dg_ws:
            try:
                data = json.loads(msg)
                alt = data.get("channel", {}).get("alternatives", [{}])[0]
                transcript = alt.get("transcript", "")
                is_final = data.get("is_final", False)
                if transcript:
                    tag = "FINAL" if is_final else "interim"
                    print(f"[Deepgram] [{tag}] {transcript}", file=sys.stderr, flush=True)
                    await session.handle_deepgram_transcript(transcript, is_final)
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Deepgram parse error: {e}")
    except Exception as e:
        print(f"[Deepgram] Reader stopped: {e}", file=sys.stderr, flush=True)


@app.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket):
    """
    Audio pipeline WebSocket for real-time voice interaction.

    Frontend sends:
      - Binary frames: 512 samples of int16 PCM at 16kHz (1024 bytes)
      - JSON text: control messages (start_session, avatar_speaking, avatar_done)

    Backend sends:
      - interim_transcript: live transcription updates
      - vad_speech_end: final transcript + LLM response + audio URL
      - interrupt_detected: speech detected during avatar playback
      - vad_speech_start: speech activity started
    """
    import sys
    await websocket.accept()
    print("[Audio WS] Client connected", file=sys.stderr, flush=True)

    session = TutorSession(
        websocket=websocket,
        tts_service=pocket_tts_service,
    )

    deepgram_ws = None
    reader_task = None
    frame_count = 0

    try:
        # Connect to Deepgram
        try:
            deepgram_ws = await connect_deepgram()
            session.deepgram_ws = deepgram_ws
            reader_task = asyncio.create_task(deepgram_reader(deepgram_ws, session))
            print("[Audio WS] Deepgram connected, reader task started", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[Audio WS] Deepgram connection FAILED: {e}", file=sys.stderr, flush=True)
            await websocket.send_json({"type": "error", "message": f"Deepgram connection failed: {e}"})

        while True:
            msg = await websocket.receive()

            if msg.get("bytes"):
                frame_count += 1
                if frame_count % 500 == 1:
                    print(f"[Audio WS] Received {frame_count} audio frames ({len(msg['bytes'])} bytes each)", file=sys.stderr, flush=True)
                # Binary audio frame
                await session.handle_audio_frame(msg["bytes"])

            elif msg.get("text"):
                # JSON control message
                try:
                    data = json.loads(msg["text"])
                    msg_type = data.get("type", "")

                    if msg_type == "start_session":
                        session.student_name = data.get("student_name", "Student")
                        session.meeting_id = data.get("meeting_id")
                        logger.info(f"Audio session started for {session.student_name}")

                    elif msg_type == "avatar_speaking":
                        session.on_avatar_speaking()

                    elif msg_type == "avatar_done":
                        session.on_avatar_done()

                except json.JSONDecodeError:
                    pass

    except Exception as e:
        logger.info(f"Audio WebSocket closed: {e}")
    finally:
        if reader_task:
            reader_task.cancel()
        if deepgram_ws:
            try:
                await deepgram_ws.close()
            except Exception:
                pass
        await session.close()
        logger.info("Audio WebSocket cleanup complete")


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    """
    Main WebSocket endpoint for real-time communication with Electron frontend

    Message format:
    {
        "type": "MESSAGE_TYPE",
        "payload": {...}
    }
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            payload = data.get("payload", {})

            logger.info(f"Received message: {message_type}")

            # Route message to appropriate handler
            response = await handle_message(message_type, payload, db)

            # Send response back to client
            if response:
                await manager.send_message(websocket, response)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_message(message_type: str, payload: dict, db: AsyncSession) -> dict:
    """
    Route WebSocket messages to appropriate handlers
    """
    handlers = {
        "PING": handle_ping,
        "GET_STUDENTS": handle_get_students,
        # Student client handlers
        "REGISTER_STUDENT": handle_register_student,
        "STUDENT_MESSAGE": handle_student_message,
        "TRIGGER_BREAKOUT": handle_trigger_breakout,
    }

    handler = handlers.get(message_type)
    if handler:
        return await handler(payload, db)
    else:
        logger.warning(f"Unknown message type: {message_type}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Unknown message type: {message_type}"}
        }


async def handle_ping(payload: dict, db: AsyncSession) -> dict:
    """Handle ping message"""
    return {
        "type": "PONG",
        "payload": {"timestamp": datetime.utcnow().isoformat()}
    }


async def handle_get_students(payload: dict, db: AsyncSession) -> dict:
    """Get list of students"""
    try:
        from sqlalchemy import select
        result = await db.execute(select(Student))
        students = result.scalars().all()

        return {
            "type": "STUDENTS_LIST",
            "payload": {
                "students": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "email": s.email
                    }
                    for s in students
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error getting students: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to get students: {str(e)}"}
        }


# ============ Student Client Handlers ============

# Store registered students by email for quick lookup
registered_students: dict = {}  # email -> {name, websocket_id, session_info}


async def handle_register_student(payload: dict, db: AsyncSession) -> dict:
    """
    Register a student client for breakout room notifications

    Payload:
    {
        "name": str,
        "email": str
    }
    """
    try:
        name = payload.get("name", "Student")
        email = payload.get("email", "")
        zoom_email = payload.get("zoom_email", email)

        # Store student registration
        registered_students[email] = {
            "name": name,
            "email": email,
            "zoom_email": zoom_email,
            "registered_at": datetime.utcnow().isoformat(),
            "avatar_session": None
        }

        logger.info(f"Student registered: {name} ({email})")

        return {
            "type": "STUDENT_REGISTERED",
            "payload": {
                "name": name,
                "email": email,
                "message": "Successfully registered for AI tutoring"
            }
        }
    except Exception as e:
        logger.error(f"Error registering student: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to register: {str(e)}"}
        }


async def handle_student_message(payload: dict, db: AsyncSession) -> dict:
    """
    Handle a message from student to avatar

    Payload:
    {
        "sessionId": str,
        "studentName": str,
        "message": str
    }
    """
    try:
        session_id = payload.get("sessionId")
        student_name = payload.get("studentName")
        message = payload.get("message")

        logger.info(f"Student message from {student_name}: {message}")

        # TODO: Send to HeyGen avatar for response
        # For now, simulate a response
        
        # In production, this would call HeyGen streaming.task API
        # and the avatar response would be sent via AVATAR_RESPONSE message
        
        return {
            "type": "MESSAGE_RECEIVED",
            "payload": {
                "sessionId": session_id,
                "status": "processing"
            }
        }
    except Exception as e:
        logger.error(f"Error handling student message: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to send message: {str(e)}"}
        }


async def handle_trigger_breakout(payload: dict, db: AsyncSession) -> dict:
    """
    Manually trigger breakout room activation for all registered students
    (Used for testing or when professor triggers from their dashboard)

    Payload:
    {
        "session_id": int (optional),
        "meeting_id": str (optional)
    }
    """
    try:
        from integrations.heygen_api_adapter import HeyGenAPIAdapter
        
        heygen = HeyGenAPIAdapter()
        
        # Create HeyGen sessions for all registered students
        results = []
        for email, student_info in registered_students.items():
            try:
                # Create a HeyGen avatar session for this student
                # If no API key, use mock session for demo
                if not heygen.api_key:
                    avatar_session = {
                        "session_id": f"mock-session-{email}",
                        "url": "wss://mock.livekit.cloud",
                        "access_token": "mock-token-for-demo"
                    }
                    logger.info(f"Using mock avatar session for {email} (no HeyGen API key)")
                else:
                    # Create session - streaming.new returns LiveKit credentials directly
                    # No need to call streaming.start when using LiveKit
                    avatar_session = await heygen.create_streaming_avatar(
                        quality="medium"
                    )
                    logger.info(f"Created avatar session, LiveKit URL: {avatar_session.get('url')}")
                
                if avatar_session:
                    student_info["avatar_session"] = avatar_session
                    
                    results.append({
                        "email": email,
                        "name": student_info["name"],
                        "avatar_session_id": avatar_session.get("session_id"),
                        "status": "created"
                    })
                    
                    logger.info(f"Created avatar session for {email}")
            except Exception as e:
                logger.error(f"Failed to create avatar for {email}: {e}")
                results.append({
                    "email": email,
                    "name": student_info["name"],
                    "status": "failed",
                    "error": str(e)
                })

        # Broadcast breakout event to all clients
        for email, student_info in registered_students.items():
            if student_info.get("avatar_session"):
                avatar = student_info["avatar_session"]
                await manager.broadcast({
                    "type": "BREAKOUT_STARTED",
                    "payload": {
                        "studentEmail": email,
                        "studentName": student_info["name"],
                        "avatarSession": {
                            "session_id": avatar.get("session_id"),
                            "livekit_url": avatar.get("url"),
                            "access_token": avatar.get("access_token")
                        }
                    }
                })

        logger.info(f"Triggered breakout for {len(results)} students")

        return {
            "type": "BREAKOUT_TRIGGERED",
            "payload": {
                "students": results,
                "count": len(results)
            }
        }
    except Exception as e:
        logger.error(f"Error triggering breakout: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to trigger breakout: {str(e)}"}
        }


# ============ Zoom Chatbot Webhook Endpoint ============

# Store video output directory for quiz generation
quiz_video_output_dir: str = os.getenv("QUIZ_VIDEO_OUTPUT_DIR", "output")


async def trigger_video_playback(student_jid: str, concept: str, video_path: str):
    """
    Callback to trigger video playback in Electron app.
    Broadcasts WebSocket message to all connected clients.
    """
    # Find registered student by JID or email pattern
    student_email = None
    for email, info in registered_students.items():
        # JID often contains email-like identifier
        if email in student_jid or student_jid in email:
            student_email = email
            break

    await manager.broadcast({
        "type": "PLAY_EXPLAINER_VIDEO",
        "payload": {
            "student_jid": student_jid,
            "student_email": student_email,
            "concept": concept,
            "video_path": video_path,
            "video_url": f"/static/videos/{os.path.basename(video_path)}" if video_path else None
        }
    })
    logger.info(f"Triggered video playback for {student_jid}: {concept}")


@app.post("/webhook/zoom-chatbot")
async def zoom_chatbot_webhook(request: dict):
    """
    Handle Zoom Team Chat chatbot webhook events.

    Events:
    - endpoint.url_validation: Verify webhook URL
    - bot_installed: Bot added to account
    - bot_notification: User messages bot or uses slash command
    - interactive_message_actions: Button clicked
    - app_deauthorized: Bot removed
    """
    try:
        event = request.get("event", "")
        payload = request.get("payload", {})

        logger.info(f"Chatbot webhook received: {event}")

        # Handle URL validation (no signature verification needed)
        if event == "endpoint.url_validation":
            plain_token = payload.get("plainToken")
            if plain_token:
                response = generate_url_validation_response(plain_token)
                logger.info("Chatbot URL validation successful")
                return response
            return {"error": "Missing plainToken"}

        # Handle bot installed
        if event == "bot_installed":
            logger.info(f"Chatbot installed for account: {payload.get('accountId')}")
            return {"success": True}

        # Handle bot notification (slash commands, DMs)
        if event == "bot_notification":
            return await handle_chatbot_notification(payload)

        # Handle button clicks
        if event == "interactive_message_actions":
            return await handle_chatbot_button_click(payload)

        # Handle app deauthorized
        if event == "app_deauthorized":
            logger.info(f"Chatbot removed from account: {payload.get('accountId')}")
            return {"success": True}

        logger.info(f"Unhandled chatbot event: {event}")
        return {"success": True}

    except Exception as e:
        logger.error(f"Chatbot webhook error: {e}")
        return {"status": "error", "message": str(e)}


async def handle_chatbot_notification(payload: dict) -> dict:
    """
    Handle bot_notification event (slash commands, DMs).

    Payload contains:
    - toJid: Where to send response
    - cmd: User's input text
    - accountId: Account ID
    - userName: User's name
    """
    to_jid = payload.get("toJid")
    cmd = payload.get("cmd", "").strip().lower()
    account_id = payload.get("accountId")
    user_name = payload.get("userName", "Student")

    logger.info(f"Chatbot command from {user_name}: {cmd}")

    # Handle /quiz command
    if cmd.startswith("quiz") or cmd == "":
        # Check if already in a quiz
        existing_session = get_quiz_session(to_jid)
        if existing_session:
            from services.zoom_chatbot_service import send_text_message
            await send_text_message(
                to_jid=to_jid,
                account_id=account_id,
                text="You already have an active quiz! Answer the current question or type 'cancel' to quit."
            )
            return {"success": True}

        # Load concepts from video output directory
        try:
            mapping = load_concept_video_mapping(quiz_video_output_dir)
            if not mapping:
                from services.zoom_chatbot_service import send_text_message
                await send_text_message(
                    to_jid=to_jid,
                    account_id=account_id,
                    text="No lecture content available yet. Please wait for the professor to set up the quiz."
                )
                return {"success": True}

            # Convert mapping to concepts list
            concepts = [
                {
                    "concept": name,
                    "description": data["description"],
                    "video_path": data.get("video_path")
                }
                for name, data in mapping.items()
            ]

            # Generate quiz
            quiz = await generate_quiz_from_concepts(
                concepts=concepts,
                num_questions=min(5, len(concepts)),
                topic="Lecture Quiz"
            )

            # Create session with video callback
            create_quiz_session(
                student_jid=to_jid,
                account_id=account_id,
                quiz=quiz,
                on_play_video=trigger_video_playback
            )

            # Send quiz intro
            await send_quiz_intro(
                to_jid=to_jid,
                account_id=account_id,
                topic=quiz.topic,
                num_questions=len(quiz.questions)
            )

            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to generate quiz: {e}")
            from services.zoom_chatbot_service import send_text_message
            await send_text_message(
                to_jid=to_jid,
                account_id=account_id,
                text=f"Sorry, I couldn't generate a quiz right now. Please try again later."
            )
            return {"success": True}

    # Handle cancel command
    if cmd == "cancel":
        await cancel_quiz(to_jid)
        return {"success": True}

    # Handle help command
    if cmd == "help":
        from services.zoom_chatbot_service import send_text_message
        await send_text_message(
            to_jid=to_jid,
            account_id=account_id,
            text="Commands:\n- /quiz: Start a quiz\n- cancel: Cancel current quiz\n- help: Show this message"
        )
        return {"success": True}

    # Default response
    from services.zoom_chatbot_service import send_text_message
    await send_text_message(
        to_jid=to_jid,
        account_id=account_id,
        text=f"Hi {user_name}! Type /quiz to start a quiz on the lecture material."
    )
    return {"success": True}


async def handle_chatbot_button_click(payload: dict) -> dict:
    """
    Handle interactive_message_actions event (button clicks).

    Payload contains:
    - actionItem: {text, value} - the button clicked
    - toJid: User's JID
    - accountId: Account ID
    - userName: User's name
    """
    action_item = payload.get("actionItem", {})
    action_value = action_item.get("value", "")
    to_jid = payload.get("toJid")
    account_id = payload.get("accountId")
    user_name = payload.get("userName", "Student")

    logger.info(f"Button click from {user_name}: {action_value}")

    # Handle start quiz button
    if action_value == "start_quiz":
        session = get_quiz_session(to_jid)
        if session:
            await start_quiz(to_jid)
        return {"success": True}

    # Handle cancel quiz button
    if action_value == "cancel_quiz":
        await cancel_quiz(to_jid)
        return {"success": True}

    # Handle answer buttons (answer_A_questionId)
    answer_letter, question_id = parse_answer_value(action_value)
    if answer_letter and question_id:
        result = await handle_answer(
            student_jid=to_jid,
            question_id=question_id,
            answer=answer_letter
        )
        logger.info(f"Answer result: {result}")
        return {"success": True}

    logger.warning(f"Unknown button action: {action_value}")
    return {"success": True}


@app.post("/api/quiz/video-completed")
async def quiz_video_completed(data: dict):
    """
    Called when student finishes watching an explainer video.
    Triggers follow-up question.

    Body:
    {
        "student_jid": str
    }
    """
    student_jid = data.get("student_jid")
    if not student_jid:
        raise HTTPException(status_code=400, detail="Missing student_jid")

    result = await handle_video_completed(student_jid)
    return result


@app.post("/api/quiz/launch")
async def launch_quiz():
    """
    Generate quiz from loaded lecture concepts and send to all registered students
    via Zoom Team Chat chatbot. Called from professor dashboard.
    """
    logger.info("Launching quiz to all registered students via Zoom Team Chat")

    # Load concepts
    mapping = load_concept_video_mapping(quiz_video_output_dir)
    if not mapping:
        raise HTTPException(status_code=400, detail="No lecture content loaded. Load a pipeline output first.")

    concepts = [
        {"concept": name, "description": info["description"], "video_path": info.get("video_path")}
        for name, info in mapping.items()
    ]

    # Generate quiz
    try:
        quiz = await generate_quiz_from_concepts(
            concepts=concepts,
            num_questions=min(5, len(concepts)),
            topic=get_lecture_context().get("topic", "Lecture Quiz")
        )
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")

    # Send to each registered student
    account_id = os.getenv("ZOOM_CHATBOT_ACCOUNT_ID", "")
    students_sent = 0
    errors = []

    for email, info in registered_students.items():
        zoom_email = info.get("zoom_email", email)
        try:
            jid = await get_user_jid(zoom_email)
            if not jid:
                errors.append(f"No JID for {zoom_email}")
                continue

            # Create quiz session with video playback callback
            create_quiz_session(
                student_jid=jid,
                account_id=account_id,
                quiz=quiz,
                on_play_video=trigger_video_playback,
            )

            # Send quiz intro
            await send_quiz_intro(
                to_jid=jid,
                account_id=account_id,
                topic=quiz.topic,
                num_questions=len(quiz.questions),
            )

            students_sent += 1
            logger.info(f"Quiz sent to {info['name']} ({jid})")
        except Exception as e:
            errors.append(f"{info['name']}: {str(e)}")
            logger.error(f"Failed to send quiz to {email}: {e}")

    # Always return success - students can use /makequiz themselves if DM failed
    return {
        "success": True,
        "students_sent": students_sent,
        "students_total": len(registered_students),
        "quiz_id": quiz.id,
        "question_count": len(quiz.questions),
        "message": f"Quiz ready! {students_sent}/{len(registered_students)} students notified via DM. Others can type /makequiz in Zoom Team Chat.",
        "errors": errors if students_sent < len(registered_students) else [],
    }


@app.get("/api/quiz/session/{student_jid}")
async def get_quiz_session_api(student_jid: str):
    """Get quiz session stats for a student."""
    stats = get_session_stats(student_jid)
    if not stats:
        raise HTTPException(status_code=404, detail="No active quiz session")
    return stats


@app.post("/api/quiz/generate")
async def generate_quiz_api(data: dict):
    """
    Generate a quiz from concepts.

    Body:
    {
        "concepts": [{"concept": str, "description": str, "video_path": str?}],
        "num_questions": int (optional),
        "topic": str (optional)
    }
    """
    concepts = data.get("concepts", [])
    num_questions = data.get("num_questions")
    topic = data.get("topic", "Quiz")

    if not concepts:
        raise HTTPException(status_code=400, detail="No concepts provided")

    try:
        quiz = await generate_quiz_from_concepts(
            concepts=concepts,
            num_questions=num_questions,
            topic=topic
        )
        return {
            "quiz_id": quiz.id,
            "topic": quiz.topic,
            "questions": [
                {
                    "id": q.id,
                    "concept": q.concept,
                    "question": q.question_text,
                    "options": q.options,
                    "video_path": q.video_path
                }
                for q in quiz.questions
            ]
        }
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quiz/load-videos")
async def load_quiz_videos(data: dict):
    """
    Load videos from Manim pipeline output directory.
    Copies/links videos to static directory for serving.

    Body:
    {
        "output_dir": str (path to pipeline output, e.g., "output" or "/path/to/output")
    }
    """
    global quiz_video_output_dir
    import shutil
    from pathlib import Path

    output_dir = data.get("output_dir", quiz_video_output_dir)
    output_path = Path(output_dir)

    if not output_path.exists():
        raise HTTPException(status_code=404, detail=f"Output directory not found: {output_dir}")

    # Load concept mapping
    mapping = load_concept_video_mapping(output_dir)
    if not mapping:
        raise HTTPException(status_code=404, detail="No concepts found in output directory")

    # Copy videos to static directory
    videos_static_dir = Path(static_dir) / "videos"
    copied_videos = []

    for concept, data_item in mapping.items():
        video_path = data_item.get("video_path")
        if video_path and Path(video_path).exists():
            video_filename = Path(video_path).name
            dest_path = videos_static_dir / video_filename

            # Copy if not already there
            if not dest_path.exists():
                shutil.copy2(video_path, dest_path)
                logger.info(f"Copied video: {video_filename}")

            copied_videos.append({
                "concept": concept,
                "filename": video_filename,
                "url": f"/static/videos/{video_filename}"
            })

    # Update global output dir
    quiz_video_output_dir = output_dir

    logger.info(f"Loaded {len(copied_videos)} videos from {output_dir}")

    return {
        "success": True,
        "output_dir": output_dir,
        "videos": copied_videos,
        "count": len(copied_videos)
    }


@app.get("/api/quiz/videos")
async def list_quiz_videos():
    """List available quiz videos."""
    from pathlib import Path

    videos_dir = Path(static_dir) / "videos"
    videos = []

    if videos_dir.exists():
        for video_file in videos_dir.glob("*.mp4"):
            videos.append({
                "filename": video_file.name,
                "url": f"/static/videos/{video_file.name}",
                "size_mb": round(video_file.stat().st_size / 1024 / 1024, 2)
            })

    return {
        "videos": videos,
        "count": len(videos),
        "output_dir": quiz_video_output_dir
    }


@app.post("/api/quiz/set-output-dir")
async def set_quiz_output_dir(data: dict):
    """
    Set the quiz video output directory.

    Body:
    {
        "output_dir": str
    }
    """
    global quiz_video_output_dir
    output_dir = data.get("output_dir")

    if not output_dir:
        raise HTTPException(status_code=400, detail="Missing output_dir")

    quiz_video_output_dir = output_dir
    logger.info(f"Quiz output directory set to: {output_dir}")

    return {"success": True, "output_dir": quiz_video_output_dir}


# ============ RTMS API Endpoints ============

@app.post("/api/rtms/session-start")
async def rtms_session_start(data: dict):
    """
    Handle RTMS session start notification from Node.js service

    Body:
    {
        "meeting_uuid": str,
        "rtms_stream_id": str,
        "room_id": int (optional)
    }
    """
    try:
        meeting_uuid = data.get("meeting_uuid")
        rtms_stream_id = data.get("rtms_stream_id")
        room_id = data.get("room_id")

        logger.info(f"RTMS session started for meeting {meeting_uuid}")

        # Define callback for transcript updates
        async def on_transcript(speaker_name: str, text: str, transcript_entry: dict):
            """Forward transcript to HeyGen avatar if room_id is associated"""
            if room_id:
                await heygen_controller.update_avatar_context_from_transcript(
                    room_id=room_id,
                    speaker_name=speaker_name,
                    transcript_text=text,
                    respond=False  # Don't auto-respond to every utterance
                )

            # Also broadcast to frontend
            await manager.broadcast({
                "type": "RTMS_TRANSCRIPT",
                "payload": {
                    "meeting_uuid": meeting_uuid,
                    "room_id": room_id,
                    **transcript_entry
                }
            })

        # Start tracking session
        rtms_service.start_session(
            meeting_uuid=meeting_uuid,
            rtms_stream_id=rtms_stream_id,
            room_id=room_id,
            on_transcript_callback=on_transcript
        )

        return {"status": "started", "meeting_uuid": meeting_uuid}
    except Exception as e:
        logger.error(f"Error starting RTMS session: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/rtms/session-stop")
async def rtms_session_stop(data: dict):
    """
    Handle RTMS session stop notification from Node.js service

    Body:
    {
        "meeting_uuid": str
    }
    """
    try:
        meeting_uuid = data.get("meeting_uuid")
        logger.info(f"RTMS session stopped for meeting {meeting_uuid}")

        rtms_service.stop_session(meeting_uuid)

        return {"status": "stopped", "meeting_uuid": meeting_uuid}
    except Exception as e:
        logger.error(f"Error stopping RTMS session: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/rtms/transcript")
async def rtms_transcript(data: dict):
    """
    Receive transcript chunk from Node.js RTMS service

    Body:
    {
        "meeting_uuid": str,
        "speaker_name": str,
        "text": str,
        "timestamp": int,
        "room_id": int (optional)
    }
    """
    try:
        meeting_uuid = data.get("meeting_uuid")
        speaker_name = data.get("speaker_name")
        text = data.get("text")
        timestamp = data.get("timestamp")
        room_id = data.get("room_id")

        # Process transcript through service
        await rtms_service.process_transcript_chunk(
            meeting_uuid=meeting_uuid,
            speaker_name=speaker_name,
            text=text,
            timestamp=str(timestamp) if timestamp else None
        )

        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error processing transcript: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/rtms/session/{meeting_uuid}/stats")
async def rtms_session_stats(meeting_uuid: str):
    """Get RTMS session statistics"""
    try:
        stats = rtms_service.get_session_stats(meeting_uuid)
        return stats
    except Exception as e:
        logger.error(f"Error getting RTMS stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rtms/session/{meeting_uuid}/transcripts")
async def rtms_session_transcripts(meeting_uuid: str, limit: int = 10):
    """Get recent transcripts for a session"""
    try:
        context = rtms_service.get_session_context(meeting_uuid, max_entries=limit)
        recent = rtms_service.get_recent_transcripts(meeting_uuid, limit=limit)

        return {
            "meeting_uuid": meeting_uuid,
            "context": context,
            "transcripts": recent,
            "count": len(recent)
        }
    except Exception as e:
        logger.error(f"Error getting transcripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Demeanor Analysis Endpoints ============

from services.demeanor_service import DemeanorService
demeanor_service = DemeanorService()


@app.post("/api/rtms/video-frame")
async def rtms_video_frame(data: dict):
    """
    Receive a video frame from RTMS Node.js service for demeanor analysis.

    Body:
    {
        "meeting_uuid": str,
        "user_id": str,
        "user_name": str,
        "timestamp": int,
        "frame_base64": str (JPG encoded frame)
    }
    """
    import base64

    try:
        user_id = data.get("user_id", "unknown")
        user_name = data.get("user_name", "Unknown")
        frame_b64 = data.get("frame_base64", "")

        frame_bytes = base64.b64decode(frame_b64) if frame_b64 else b""

        # Run analysis
        metrics = await demeanor_service.analyze_frame(user_id, user_name, frame_bytes)

        # Broadcast to professor dashboard via WebSocket
        await manager.broadcast({
            "type": "DEMEANOR_UPDATE",
            "payload": {
                "user_id": user_id,
                "user_name": user_name,
                "engagement_score": metrics.engagement_score,
                "attention": metrics.attention,
                "expression": metrics.expression,
                "timestamp": metrics.timestamp,
            }
        })

        return {"status": "analyzed"}
    except Exception as e:
        logger.error(f"Demeanor analysis error: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/demeanor/status")
async def demeanor_status():
    """Get current per-student engagement metrics."""
    return demeanor_service.get_all_metrics()


@app.get("/api/demeanor/summary")
async def demeanor_summary():
    """Get session-level analytics summary."""
    return demeanor_service.get_session_summary()


# REST API endpoints (for non-real-time operations)

@app.get("/api/professors")
async def get_professors(db: AsyncSession = Depends(get_db)):
    """Get all professors"""
    from sqlalchemy import select
    result = await db.execute(select(Professor))
    professors = result.scalars().all()
    return [{"id": p.id, "name": p.name, "email": p.email} for p in professors]


@app.get("/api/students")
async def get_students(db: AsyncSession = Depends(get_db)):
    """Get all students"""
    from sqlalchemy import select
    result = await db.execute(select(Student))
    students = result.scalars().all()
    return [{"id": s.id, "name": s.name, "email": s.email} for s in students]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """Get session details"""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "professor_id": session.professor_id,
        "meeting_id": session.meeting_id,
        "status": session.status,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "configuration": session.configuration
    }


@app.post("/api/trigger-breakout")
async def trigger_breakout_api(db: AsyncSession = Depends(get_db)):
    """
    REST endpoint to trigger breakout rooms manually (for testing)
    """
    result = await handle_trigger_breakout({}, db)
    return result["payload"]


@app.get("/api/registered-students")
async def get_registered_students():
    """Get list of currently registered student clients"""
    return {
        "students": [
            {
                "email": email,
                "name": info["name"],
                "registered_at": info["registered_at"],
                "has_avatar": info.get("avatar_session") is not None
            }
            for email, info in registered_students.items()
        ],
        "count": len(registered_students)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

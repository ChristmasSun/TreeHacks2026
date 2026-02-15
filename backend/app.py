"""
FastAPI application with WebSocket support for Electron frontend
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import json
import logging
import os
from datetime import datetime

from models import get_db, init_db
from models.models import Professor, Student, Session, BreakoutRoom
from services.session_orchestrator import SessionOrchestrator
from services.llm_service import (
    generate_tutoring_response,
    set_lecture_context,
    get_lecture_context,
    set_active_meeting,
    get_active_meeting,
    fetch_rtms_transcripts
)
from services.tts_service import text_to_speech
from services.rtms_transcription_service import RTMSTranscriptionService
from services.heygen_controller import HeyGenController
from services.zoom_chatbot_service import (
    verify_webhook_signature,
    generate_url_validation_response,
    send_quiz_intro,
    parse_answer_value,
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
    """Initialize database on startup"""
    logger.info("Starting up application...")
    await init_db()
    logger.info("Database initialized")


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
        "CREATE_SESSION": handle_create_session,
        "END_SESSION": handle_end_session,
        "GET_SESSION_STATUS": handle_get_session_status,
        "GET_STUDENTS": handle_get_students,
        "VALIDATE_ZOOM": handle_validate_zoom,
        "GET_ROOM_TRANSCRIPTS": handle_get_room_transcripts,
        "VALIDATE_DEEPGRAM": handle_validate_deepgram,
        "PROCESS_AUDIO": handle_process_audio,
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


async def handle_create_session(payload: dict, db: AsyncSession) -> dict:
    """
    Handle session creation request

    Payload:
    {
        "professor_id": int,
        "student_ids": [int],
        "topic": str,
        "duration": int,
        "configuration": {...}
    }
    """
    try:
        orchestrator = SessionOrchestrator(
            on_transcript_callback=forward_transcript_to_frontend
        )

        # Create session with Zoom meeting and breakout rooms
        result = await orchestrator.create_breakout_session(
            db=db,
            professor_id=payload["professor_id"],
            student_ids=payload["student_ids"],
            topic=payload.get("topic", "Breakout Session"),
            duration=payload.get("duration", 20),
            configuration=payload.get("configuration", {})
        )

        logger.info(f"Session created: {result['session_id']}")

        # Broadcast to all connected clients
        await manager.broadcast({
            "type": "SESSION_CREATED",
            "payload": result
        })

        return {
            "type": "SESSION_CREATED",
            "payload": result
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to create session: {str(e)}"}
        }


async def handle_end_session(payload: dict, db: AsyncSession) -> dict:
    """Handle session end request"""
    try:
        orchestrator = SessionOrchestrator()
        session_id = payload["session_id"]

        # End session and cleanup
        result = await orchestrator.end_session(db=db, session_id=session_id)

        logger.info(f"Session ended: {session_id}")

        # Broadcast to all connected clients
        await manager.broadcast({
            "type": "SESSION_ENDED",
            "payload": result
        })

        return {
            "type": "SESSION_ENDED",
            "payload": result
        }
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to end session: {str(e)}"}
        }


async def handle_get_session_status(payload: dict, db: AsyncSession) -> dict:
    """Get current session status"""
    try:
        orchestrator = SessionOrchestrator()
        session_id = payload["session_id"]

        # Get detailed session status
        result = await orchestrator.get_session_status(db=db, session_id=session_id)

        return {
            "type": "SESSION_STATUS",
            "payload": result
        }
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to get session status: {str(e)}"}
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


async def handle_validate_zoom(payload: dict, db: AsyncSession) -> dict:
    """Validate Zoom API credentials"""
    try:
        orchestrator = SessionOrchestrator()
        is_valid = await orchestrator.validate_zoom_connection()

        return {
            "type": "ZOOM_VALIDATION",
            "payload": {
                "valid": is_valid,
                "message": "Zoom credentials are valid" if is_valid else "Zoom credentials are invalid"
            }
        }
    except Exception as e:
        logger.error(f"Error validating Zoom: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to validate Zoom: {str(e)}"}
        }


async def handle_validate_deepgram(payload: dict, db: AsyncSession) -> dict:
    """Validate Deepgram API credentials"""
    try:
        orchestrator = SessionOrchestrator()
        is_valid = await orchestrator.validate_transcription_service()

        return {
            "type": "DEEPGRAM_VALIDATION",
            "payload": {
                "valid": is_valid,
                "message": "Deepgram credentials are valid" if is_valid else "Deepgram credentials are invalid"
            }
        }
    except Exception as e:
        logger.error(f"Error validating Deepgram: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to validate Deepgram: {str(e)}"}
        }


async def handle_get_room_transcripts(payload: dict, db: AsyncSession) -> dict:
    """
    Get transcripts for a specific room

    Payload:
    {
        "room_id": int,
        "limit": int (optional, default 100)
    }
    """
    try:
        room_id = payload["room_id"]
        limit = payload.get("limit", 100)

        orchestrator = SessionOrchestrator()
        transcripts = await orchestrator.get_room_transcripts(
            db=db,
            room_id=room_id,
            limit=limit
        )

        return {
            "type": "ROOM_TRANSCRIPTS",
            "payload": {
                "room_id": room_id,
                "transcripts": transcripts,
                "count": len(transcripts)
            }
        }
    except Exception as e:
        logger.error(f"Error getting room transcripts: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to get room transcripts: {str(e)}"}
        }


async def handle_process_audio(payload: dict, db: AsyncSession) -> dict:
    """
    Process audio chunk from HeyGen avatar

    Payload:
    {
        "room_id": int,
        "audio_data": bytes (base64 encoded)
    }
    """
    try:
        import base64

        room_id = payload["room_id"]
        audio_data_b64 = payload["audio_data"]

        # Decode base64 audio data
        audio_data = base64.b64decode(audio_data_b64)

        orchestrator = SessionOrchestrator()
        success = await orchestrator.process_audio_for_room(
            room_id=room_id,
            audio_data=audio_data
        )

        return {
            "type": "AUDIO_PROCESSED",
            "payload": {
                "room_id": room_id,
                "success": success
            }
        }
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return {
            "type": "ERROR",
            "payload": {"message": f"Failed to process audio: {str(e)}"}
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

        # Store student registration
        registered_students[email] = {
            "name": name,
            "email": email,
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


# ============ Zoom Webhook Endpoint ============

@app.post("/webhook/zoom")
async def zoom_webhook(request_data: dict):
    """
    Handle Zoom webhook events (breakout rooms, meeting events, etc.)

    Events we care about:
    - meeting.participant_joined_breakout_room
    - meeting.breakout_room_opened
    - meeting.rtms_started
    - meeting.rtms_stopped
    """
    try:
        event = request_data.get("event", "")
        payload = request_data.get("payload", {})

        logger.info(f"Zoom webhook received: {event}")

        if event == "meeting.breakout_room_opened":
            # Breakout rooms were opened by the host
            logger.info("Breakout rooms opened! Notifying students...")

            # Trigger avatar creation and notification
            await handle_trigger_breakout({}, None)

        elif event == "meeting.participant_joined_breakout_room":
            # A participant joined a breakout room
            participant = payload.get("object", {}).get("participant", {})
            room_name = payload.get("object", {}).get("breakout_room", {}).get("name", "")

            logger.info(f"Participant {participant.get('user_name')} joined breakout room: {room_name}")

        elif event in ["meeting.rtms_started", "webinar.rtms_started", "session.rtms_started"]:
            # Forward to Node.js RTMS service
            logger.info(f"RTMS started event received, forwarding to RTMS service")
            # Note: The Node.js service will handle the actual RTMS connection
            # This webhook acknowledgment is required by Zoom

        elif event in ["meeting.rtms_stopped", "webinar.rtms_stopped", "session.rtms_stopped"]:
            logger.info(f"RTMS stopped event received")

        return {"status": "received"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


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
    global quiz_video_output_dir
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

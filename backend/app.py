"""
FastAPI application with WebSocket support for Electron frontend
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import json
import logging
from datetime import datetime

from models import get_db, init_db
from models.models import Professor, Student, Session, BreakoutRoom
from services.session_orchestrator import SessionOrchestrator

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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": len(manager.active_connections)
    }


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

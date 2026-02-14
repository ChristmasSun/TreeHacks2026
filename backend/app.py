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
        "meeting_id": str,
        "student_ids": [int],
        "configuration": {...}
    }
    """
    try:
        # Create session record
        new_session = Session(
            professor_id=payload["professor_id"],
            meeting_id=payload["meeting_id"],
            status="initializing",
            configuration=payload.get("configuration", {})
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        logger.info(f"Session created: {new_session.id}")

        # TODO: Trigger session orchestrator to:
        # 1. Create Zoom breakout rooms
        # 2. Deploy HeyGen avatars
        # 3. Start transcription streams

        return {
            "type": "SESSION_CREATED",
            "payload": {
                "session_id": new_session.id,
                "status": "initializing",
                "message": "Session created successfully"
            }
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
        session_id = payload["session_id"]

        # Update session status
        session = await db.get(Session, session_id)
        if session:
            session.status = "completed"
            session.end_time = datetime.utcnow()
            await db.commit()

            logger.info(f"Session ended: {session_id}")

            # TODO: Trigger cleanup:
            # 1. Close transcription streams
            # 2. Disconnect HeyGen avatars
            # 3. Generate analytics

            return {
                "type": "SESSION_ENDED",
                "payload": {
                    "session_id": session_id,
                    "message": "Session ended successfully"
                }
            }
        else:
            return {
                "type": "ERROR",
                "payload": {"message": "Session not found"}
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
        session_id = payload["session_id"]
        session = await db.get(Session, session_id)

        if session:
            return {
                "type": "SESSION_STATUS",
                "payload": {
                    "session_id": session.id,
                    "status": session.status,
                    "start_time": session.start_time.isoformat() if session.start_time else None,
                    "end_time": session.end_time.isoformat() if session.end_time else None
                }
            }
        else:
            return {
                "type": "ERROR",
                "payload": {"message": "Session not found"}
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

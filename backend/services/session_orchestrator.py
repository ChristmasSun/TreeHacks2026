"""
Session Orchestrator
Coordinates all services for breakout session lifecycle
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Session, Professor, Student, BreakoutRoom
from services.zoom_manager import ZoomManager

logger = logging.getLogger(__name__)


class SessionOrchestrator:
    """
    Orchestrates the entire breakout session lifecycle:
    1. Create Zoom meeting with breakout rooms
    2. Deploy HeyGen avatars (future phase)
    3. Start transcription streams (future phase)
    4. Monitor session health
    5. Generate analytics on completion
    """

    def __init__(self, zoom_manager: Optional[ZoomManager] = None):
        self.zoom_manager = zoom_manager or ZoomManager()

    async def create_breakout_session(
        self,
        db: AsyncSession,
        professor_id: int,
        student_ids: List[int],
        topic: str,
        duration: int = 20,
        configuration: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a complete breakout session

        Args:
            db: Database session
            professor_id: Professor ID
            student_ids: List of student IDs
            topic: Session topic
            duration: Duration in minutes
            configuration: Additional configuration

        Returns:
            Session details with meeting and room assignments
        """
        try:
            # Step 1: Get professor and students from database
            professor = await db.get(Professor, professor_id)
            if not professor:
                raise ValueError(f"Professor {professor_id} not found")

            students = []
            for student_id in student_ids:
                student = await db.get(Student, student_id)
                if student:
                    students.append(student)
                else:
                    logger.warning(f"Student {student_id} not found, skipping")

            if not students:
                raise ValueError("No valid students found")

            logger.info(
                f"Creating session for professor {professor.name} "
                f"with {len(students)} students"
            )

            # Step 2: Create Zoom meeting with breakout rooms
            host_user_id = professor.zoom_user_id or professor.email
            meeting_result = await self.zoom_manager.create_meeting_with_breakout_rooms(
                host_user_id=host_user_id,
                topic=topic,
                students=students,
                duration=duration
            )

            # Step 3: Create session record in database
            session = Session(
                professor_id=professor_id,
                meeting_id=meeting_result["meeting_id"],
                status="active",
                configuration=configuration or {}
            )
            db.add(session)
            await db.flush()  # Get session.id

            # Step 4: Create breakout room records
            zoom_rooms = meeting_result.get("breakout_rooms", [])
            breakout_rooms = []

            for idx, student in enumerate(students):
                # Match student to their Zoom room
                zoom_room = zoom_rooms[idx] if idx < len(zoom_rooms) else None
                zoom_room_id = zoom_room.get("id") if zoom_room else f"room_{idx}"

                room = BreakoutRoom(
                    session_id=session.id,
                    zoom_room_id=zoom_room_id,
                    student_id=student.id,
                    status="pending"  # Will be "active" when avatars join
                )
                db.add(room)
                breakout_rooms.append(room)

            await db.commit()
            await db.refresh(session)

            logger.info(f"Session {session.id} created successfully")

            # Step 5: TODO - Deploy HeyGen avatars (Phase 3)
            # Step 6: TODO - Start transcription streams (Phase 4)

            return {
                "session_id": session.id,
                "meeting_id": meeting_result["meeting_id"],
                "join_url": meeting_result["join_url"],
                "start_url": meeting_result.get("start_url"),
                "topic": topic,
                "duration": duration,
                "status": "active",
                "breakout_rooms": [
                    {
                        "room_id": room.id,
                        "zoom_room_id": room.zoom_room_id,
                        "student_id": room.student_id,
                        "student_name": students[idx].name if idx < len(students) else "Unknown",
                        "status": room.status
                    }
                    for idx, room in enumerate(breakout_rooms)
                ],
                "message": "Session created successfully. HeyGen avatars will be deployed next."
            }

        except Exception as e:
            logger.error(f"Failed to create breakout session: {e}")
            await db.rollback()
            raise

    async def end_session(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Dict[str, Any]:
        """
        End a breakout session

        Args:
            db: Database session
            session_id: Session ID

        Returns:
            Session summary
        """
        try:
            # Get session
            session = await db.get(Session, session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Update session status
            session.status = "completed"
            session.end_time = datetime.utcnow()

            # TODO: Close transcription streams (Phase 4)
            # TODO: Disconnect HeyGen avatars (Phase 3)

            # Update breakout room statuses
            result = await db.execute(
                select(BreakoutRoom).where(BreakoutRoom.session_id == session_id)
            )
            rooms = result.scalars().all()

            for room in rooms:
                room.status = "completed"

            await db.commit()

            logger.info(f"Session {session_id} ended successfully")

            # TODO: Generate analytics (Phase 7)

            return {
                "session_id": session_id,
                "status": "completed",
                "total_rooms": len(rooms),
                "message": "Session ended successfully. Analytics will be generated."
            }

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            await db.rollback()
            raise

    async def get_session_status(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Get current session status with room details
        """
        try:
            session = await db.get(Session, session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Get breakout rooms
            result = await db.execute(
                select(BreakoutRoom).where(BreakoutRoom.session_id == session_id)
            )
            rooms = result.scalars().all()

            # Get room details with student info
            room_details = []
            for room in rooms:
                student = await db.get(Student, room.student_id)
                room_details.append({
                    "room_id": room.id,
                    "zoom_room_id": room.zoom_room_id,
                    "student_name": student.name if student else "Unknown",
                    "student_email": student.email if student else None,
                    "avatar_session_id": room.avatar_session_id,
                    "status": room.status
                })

            return {
                "session_id": session.id,
                "meeting_id": session.meeting_id,
                "status": session.status,
                "start_time": session.start_time.isoformat() if session.start_time else None,
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "configuration": session.configuration,
                "breakout_rooms": room_details
            }

        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            raise

    async def monitor_session_health(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Dict[str, Any]:
        """
        Check health of active session
        Returns alerts for rooms that need attention
        """
        try:
            session = await db.get(Session, session_id)
            if not session or session.status != "active":
                return {"status": "inactive", "alerts": []}

            # TODO: Implement health checks
            # - Check if avatars are still connected
            # - Check transcription streams are active
            # - Detect idle rooms (no conversation)
            # - Detect confused students (repeated questions)

            alerts = []

            return {
                "session_id": session_id,
                "status": "healthy",
                "alerts": alerts,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to monitor session health: {e}")
            raise

    async def validate_zoom_connection(self) -> bool:
        """
        Validate Zoom API connection
        """
        return await self.zoom_manager.validate_connection()

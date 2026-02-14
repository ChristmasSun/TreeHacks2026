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
from services.heygen_controller import HeyGenController
from services.transcription_service import get_transcription_service

logger = logging.getLogger(__name__)


class SessionOrchestrator:
    """
    Orchestrates the entire breakout session lifecycle:
    1. Create Zoom meeting with breakout rooms
    2. Deploy HeyGen avatars
    3. Start transcription streams (Phase 4)
    4. Monitor session health
    5. Generate analytics on completion
    """

    def __init__(
        self,
        zoom_manager: Optional[ZoomManager] = None,
        heygen_controller: Optional[HeyGenController] = None,
        on_transcript_callback: Optional[Any] = None
    ):
        self.zoom_manager = zoom_manager or ZoomManager()
        self.heygen_controller = heygen_controller or HeyGenController()
        self.transcription_service = get_transcription_service(
            on_transcript_callback=on_transcript_callback
        )

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

            # Refresh breakout rooms to get IDs
            for room in breakout_rooms:
                await db.refresh(room)

            logger.info(f"Session {session.id} created successfully")

            # Step 5: Deploy HeyGen avatars to breakout rooms
            avatar_deployment_result = None
            try:
                # Build students map for avatar deployment
                students_map = {s.id: s for s in students}

                # Deploy avatars in parallel
                avatar_deployment_result = await self.heygen_controller.deploy_avatars_to_rooms(
                    rooms=breakout_rooms,
                    professor=professor,
                    students_map=students_map,
                    context=configuration.get("course_context") if configuration else None
                )

                # Update breakout room records with avatar session IDs
                for deployment in avatar_deployment_result.get("deployments", []):
                    room_id = deployment.get("room_id")
                    session_id = deployment.get("session_id")

                    if room_id and session_id:
                        for room in breakout_rooms:
                            if room.id == room_id:
                                room.avatar_session_id = session_id
                                room.status = "active"
                                break

                await db.commit()

                logger.info(
                    f"Avatar deployment: {avatar_deployment_result.get('successful', 0)} "
                    f"successful, {avatar_deployment_result.get('failed', 0)} failed"
                )

            except Exception as e:
                logger.error(f"Failed to deploy avatars: {e}")
                # Continue anyway - session still usable without avatars

            # Step 6: Start transcription streams (Phase 4)
            # Transcription integrates with HeyGen avatar audio streams
            transcription_results = []
            for room in breakout_rooms:
                try:
                    success = await self.transcription_service.start_room_transcription(
                        db=db,
                        room_id=room.id,
                        language="en-US"  # TODO: Make configurable per session
                    )
                    if success:
                        logger.info(f"Started transcription for room {room.id}")
                        transcription_results.append({"room_id": room.id, "status": "started"})
                    else:
                        logger.warning(f"Failed to start transcription for room {room.id}")
                        transcription_results.append({"room_id": room.id, "status": "failed"})
                except Exception as e:
                    logger.error(f"Error starting transcription for room {room.id}: {e}")
                    transcription_results.append({"room_id": room.id, "status": "error", "error": str(e)})

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
                        "avatar_session_id": room.avatar_session_id,
                        "status": room.status
                    }
                    for idx, room in enumerate(breakout_rooms)
                ],
                "avatars": {
                    "deployed": avatar_deployment_result.get("successful", 0) if avatar_deployment_result else 0,
                    "failed": avatar_deployment_result.get("failed", 0) if avatar_deployment_result else 0,
                    "total": len(breakout_rooms)
                } if avatar_deployment_result else None,
                "message": f"Session created successfully. Avatars deployed: {avatar_deployment_result.get('successful', 0)}/{len(breakout_rooms)}" if avatar_deployment_result else "Session created successfully."
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

            # Get breakout rooms
            result = await db.execute(
                select(BreakoutRoom).where(BreakoutRoom.session_id == session_id)
            )
            rooms = result.scalars().all()

            # Disconnect HeyGen avatars
            room_ids = [room.id for room in rooms]
            avatar_cleanup_result = await self.heygen_controller.stop_all_avatars(room_ids)

            logger.info(
                f"Avatar cleanup: {avatar_cleanup_result.get('stopped', 0)} stopped, "
                f"{avatar_cleanup_result.get('failed', 0)} failed"
            )

            # Close transcription streams (Phase 4)
            await self.transcription_service.stop_all_transcriptions()
            logger.info(f"Stopped all transcriptions for session {session_id}")

            # Update breakout room statuses
            for room in rooms:
                room.status = "completed"

            await db.commit()

            logger.info(f"Session {session_id} ended successfully")

            # TODO: Generate analytics (Phase 7)

            return {
                "session_id": session_id,
                "status": "completed",
                "total_rooms": len(rooms),
                "avatars_stopped": avatar_cleanup_result.get("stopped", 0),
                "message": f"Session ended successfully. {avatar_cleanup_result.get('stopped', 0)} avatars disconnected."
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

    async def validate_heygen_connection(self) -> bool:
        """
        Validate HeyGen API connection
        """
        return await self.heygen_controller.validate_connection()

    async def validate_transcription_service(self) -> bool:
        """
        Validate transcription service (Deepgram) connection
        """
        return await self.transcription_service.validate_service()

    async def process_audio_for_room(
        self,
        room_id: int,
        audio_data: bytes
    ) -> bool:
        """
        Process audio chunk for a specific room from HeyGen audio pipeline
        This receives audio from HeyGen avatars and feeds it to Deepgram

        Args:
            room_id: Breakout room ID
            audio_data: Raw PCM audio (linear16, 16kHz, mono)

        Returns:
            True if audio processed successfully
        """
        return await self.transcription_service.process_audio_chunk(
            room_id=room_id,
            audio_data=audio_data
        )

    async def get_room_transcripts(
        self,
        db: AsyncSession,
        room_id: int,
        limit: int = 100
    ) -> list:
        """
        Get transcripts for a specific breakout room

        Args:
            db: Database session
            room_id: Breakout room ID
            limit: Maximum number of transcripts

        Returns:
            List of transcript dictionaries
        """
        return await self.transcription_service.get_room_transcripts(
            db=db,
            room_id=room_id,
            limit=limit
        )

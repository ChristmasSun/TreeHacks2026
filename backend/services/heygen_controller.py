"""
HeyGen Controller Service
Manages HeyGen avatar lifecycle and Zoom integration
"""
from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from integrations.heygen_api_adapter import HeyGenAPIAdapter
from services.zoom_bot_service_client import ZoomBotServiceClient
from models.models import Professor, Student, BreakoutRoom

logger = logging.getLogger(__name__)


class HeyGenController:
    """
    High-level service for managing HeyGen Interactive Avatars
    Coordinates avatar creation, Zoom integration, and lifecycle management
    """

    def __init__(
        self,
        heygen_adapter: Optional[HeyGenAPIAdapter] = None,
        bot_service_client: Optional[ZoomBotServiceClient] = None
    ):
        self.heygen = heygen_adapter or HeyGenAPIAdapter()
        self.bot_service = bot_service_client or ZoomBotServiceClient()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # room_id -> session_data

    async def validate_connection(self) -> bool:
        """
        Test HeyGen API connection and credentials
        """
        return await self.heygen.validate_credentials()

    async def create_avatar_for_room(
        self,
        room_id: int,
        professor: Professor,
        student: Student,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and configure HeyGen avatar for a specific breakout room

        Args:
            room_id: Breakout room ID
            professor: Professor object with avatar configuration
            student: Student who will interact with avatar
            context: Course context/knowledge for the avatar

        Returns:
            Avatar session details
        """
        try:
            logger.info(f"Creating avatar for room {room_id}, student {student.name}")

            # Build context for avatar
            avatar_context = self._build_avatar_context(
                professor=professor,
                student=student,
                additional_context=context
            )

            # Create avatar session
            session_data = await self.heygen.create_avatar_for_zoom(
                professor_name=professor.name,
                avatar_id=professor.heygen_avatar_id,
                context=avatar_context
            )

            session_id = session_data["session_id"]

            # Store session info
            self.active_sessions[str(room_id)] = {
                "session_id": session_id,
                "room_id": room_id,
                "professor_id": professor.id,
                "student_id": student.id,
                "status": "created",
                "created_at": datetime.utcnow().isoformat(),
                **session_data
            }

            logger.info(f"Avatar session created for room {room_id}: {session_id}")

            return {
                "room_id": room_id,
                "session_id": session_id,
                "status": "created",
                "access_token": session_data.get("access_token"),
                "ready": session_data.get("ready", False)
            }

        except Exception as e:
            logger.error(f"Failed to create avatar for room {room_id}: {e}")
            raise

    async def deploy_avatars_to_rooms(
        self,
        rooms: List[BreakoutRoom],
        professor: Professor,
        students_map: Dict[int, Student],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deploy HeyGen avatars to multiple breakout rooms in parallel

        Args:
            rooms: List of BreakoutRoom objects
            professor: Professor object
            students_map: Dict mapping student_id to Student object
            context: Shared course context

        Returns:
            Deployment results for all rooms
        """
        logger.info(f"Deploying avatars to {len(rooms)} rooms")

        # Create avatars in parallel
        tasks = []
        for room in rooms:
            student = students_map.get(room.student_id)
            if student:
                task = self.create_avatar_for_room(
                    room_id=room.id,
                    professor=professor,
                    student=student,
                    context=context
                )
                tasks.append(task)
            else:
                logger.warning(f"Student {room.student_id} not found for room {room.id}")

        # Wait for all avatars to be created
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful = []
        failed = []

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                room = rooms[idx]
                failed.append({
                    "room_id": room.id,
                    "error": str(result)
                })
                logger.error(f"Failed to deploy avatar to room {room.id}: {result}")
            else:
                successful.append(result)

        logger.info(
            f"Avatar deployment complete: {len(successful)} successful, "
            f"{len(failed)} failed"
        )

        return {
            "total_rooms": len(rooms),
            "successful": len(successful),
            "failed": len(failed),
            "deployments": successful,
            "errors": failed
        }

    async def send_message_to_avatar(
        self,
        room_id: int,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a message to avatar in a specific room

        Args:
            room_id: Breakout room ID
            message: Message for avatar to speak

        Returns:
            Task result
        """
        session_data = self.active_sessions.get(str(room_id))
        if not session_data:
            raise ValueError(f"No active avatar session for room {room_id}")

        session_id = session_data["session_id"]

        try:
            result = await self.heygen.send_message_to_avatar(
                session_id=session_id,
                message=message,
                task_mode="async"  # Non-blocking
            )

            logger.debug(f"Sent message to avatar in room {room_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to send message to avatar in room {room_id}: {e}")
            raise

    async def stop_avatar(self, room_id: int) -> bool:
        """
        Stop avatar session for a specific room

        Args:
            room_id: Breakout room ID

        Returns:
            Success status
        """
        session_data = self.active_sessions.get(str(room_id))
        if not session_data:
            logger.warning(f"No active avatar session for room {room_id}")
            return False

        session_id = session_data["session_id"]

        try:
            # Disconnect Zoom bot if active
            if "bot_id" in session_data:
                await self.disconnect_avatar_from_zoom(room_id)

            # Stop HeyGen avatar session
            await self.heygen.stop_avatar_session(session_id)
            del self.active_sessions[str(room_id)]
            logger.info(f"Stopped avatar for room {room_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop avatar for room {room_id}: {e}")
            return False

    async def stop_all_avatars(self, room_ids: List[int]) -> Dict[str, Any]:
        """
        Stop all avatar sessions for given rooms

        Args:
            room_ids: List of room IDs

        Returns:
            Cleanup results
        """
        logger.info(f"Stopping {len(room_ids)} avatar sessions")

        tasks = [self.stop_avatar(room_id) for room_id in room_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful

        logger.info(f"Avatar cleanup: {successful} stopped, {failed} failed")

        return {
            "total": len(room_ids),
            "stopped": successful,
            "failed": failed
        }

    async def get_avatar_status(self, room_id: int) -> Dict[str, Any]:
        """
        Get status of avatar in a specific room

        Args:
            room_id: Breakout room ID

        Returns:
            Avatar status details
        """
        session_data = self.active_sessions.get(str(room_id))
        if not session_data:
            return {
                "room_id": room_id,
                "status": "not_active",
                "session_id": None
            }

        session_id = session_data["session_id"]

        try:
            status = await self.heygen.get_session_status(session_id)
            return {
                "room_id": room_id,
                "session_id": session_id,
                "status": status.get("status", "unknown"),
                "created_at": session_data.get("created_at"),
                **status
            }

        except Exception as e:
            logger.error(f"Failed to get avatar status for room {room_id}: {e}")
            return {
                "room_id": room_id,
                "session_id": session_id,
                "status": "error",
                "error": str(e)
            }

    async def restart_avatar(
        self,
        room_id: int,
        professor: Professor,
        student: Student,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Restart avatar for a room (stop old session, create new one)

        Args:
            room_id: Breakout room ID
            professor: Professor object
            student: Student object
            context: Course context

        Returns:
            New session details
        """
        logger.info(f"Restarting avatar for room {room_id}")

        # Stop existing session if any
        await self.stop_avatar(room_id)

        # Create new session
        return await self.create_avatar_for_room(
            room_id=room_id,
            professor=professor,
            student=student,
            context=context
        )

    # ==================== Helper Methods ====================

    def _build_avatar_context(
        self,
        professor: Professor,
        student: Student,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Build context string for avatar with professor and student info

        Args:
            professor: Professor object
            student: Student object
            additional_context: Additional course context

        Returns:
            Formatted context string
        """
        context_parts = [
            f"You are {professor.name}, a professor helping students learn.",
            f"You are currently helping {student.name} in a 1-on-1 session.",
            "",
            "Your role:",
            "- Answer the student's questions clearly and patiently",
            "- Use the Socratic method to guide their understanding",
            "- Provide examples and explanations at their level",
            "- Encourage critical thinking",
            "",
            "Guidelines:",
            "- Keep responses concise (1-3 sentences unless asked for detail)",
            "- Ask follow-up questions to check understanding",
            "- If the student is confused, try explaining differently",
            "- Be encouraging and supportive",
        ]

        if additional_context:
            context_parts.extend([
                "",
                "Course Context:",
                additional_context
            ])

        return "\n".join(context_parts)

    def get_active_session_count(self) -> int:
        """Get count of active avatar sessions"""
        return len(self.active_sessions)

    def get_all_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active avatar sessions"""
        return self.active_sessions.copy()

    # ==================== Zoom Integration ====================

    async def connect_avatar_to_zoom(
        self,
        room_id: int,
        meeting_number: str,
        bot_name: str,
        passcode: Optional[str] = None,
        breakout_room_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Connect HeyGen avatar to Zoom via bot service

        Creates a Zoom bot that joins the meeting and acts as the avatar's
        voice in the Zoom room. Audio routing:
        - Zoom audio -> Bot -> Python backend -> Deepgram (transcription)
        - HeyGen response -> Bot -> Zoom audio (avatar speaks)

        Args:
            room_id: Internal breakout room ID
            meeting_number: Zoom meeting number
            bot_name: Display name for bot (e.g., "AI Professor - Alice")
            passcode: Meeting passcode (optional)
            breakout_room_id: Zoom breakout room ID to join (optional)

        Returns:
            Bot creation status
        """
        try:
            session_data = self.active_sessions.get(str(room_id))
            if not session_data:
                raise ValueError(f"No active avatar session for room {room_id}")

            heygen_session_id = session_data["session_id"]

            # Create bot via Node.js bot service
            bot_id = await self.bot_service.create_bot(
                meeting_number=meeting_number,
                bot_name=bot_name,
                room_id=room_id,
                passcode=passcode,
                heygen_session_id=heygen_session_id
            )

            # Update session with bot info
            self.active_sessions[str(room_id)]["bot_id"] = bot_id
            self.active_sessions[str(room_id)]["zoom_status"] = "joined"

            logger.info(f"Bot {bot_id} connected to Zoom for room {room_id}")

            # If breakout room specified, move bot there
            if breakout_room_id:
                await self.bot_service.move_bot_to_breakout_room(bot_id, breakout_room_id)
                self.active_sessions[str(room_id)]["breakout_room_id"] = breakout_room_id

            return {
                "status": "connected",
                "bot_id": bot_id,
                "room_id": room_id,
                "heygen_session_id": heygen_session_id,
                "zoom_meeting": meeting_number
            }

        except Exception as e:
            logger.error(f"Failed to connect avatar to Zoom for room {room_id}: {e}")
            raise

    async def play_avatar_audio_in_zoom(
        self,
        room_id: int,
        audio_data: bytes
    ) -> None:
        """
        Play HeyGen avatar audio through Zoom bot

        Args:
            room_id: Breakout room ID
            audio_data: Audio bytes from HeyGen
        """
        session_data = self.active_sessions.get(str(room_id))
        if not session_data or "bot_id" not in session_data:
            raise ValueError(f"No Zoom bot active for room {room_id}")

        bot_id = session_data["bot_id"]
        await self.bot_service.play_audio(bot_id, audio_data)

    async def disconnect_avatar_from_zoom(self, room_id: int) -> bool:
        """
        Disconnect Zoom bot for avatar

        Args:
            room_id: Breakout room ID

        Returns:
            Success status
        """
        session_data = self.active_sessions.get(str(room_id))
        if not session_data or "bot_id" not in session_data:
            logger.warning(f"No Zoom bot to disconnect for room {room_id}")
            return False

        bot_id = session_data["bot_id"]

        try:
            await self.bot_service.remove_bot(bot_id)
            self.active_sessions[str(room_id)]["zoom_status"] = "disconnected"
            del self.active_sessions[str(room_id)]["bot_id"]
            logger.info(f"Disconnected bot {bot_id} from room {room_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disconnect bot from room {room_id}: {e}")
            return False

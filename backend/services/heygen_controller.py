"""
HeyGen Controller Service
Manages HeyGen avatar lifecycle and Zoom integration
"""
from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from integrations.heygen_api_adapter import HeyGenAPIAdapter
from models.models import Professor, Student, BreakoutRoom

logger = logging.getLogger(__name__)


class HeyGenController:
    """
    High-level service for managing HeyGen Interactive Avatars
    Coordinates avatar creation, Zoom integration, and lifecycle management
    """

    def __init__(self, heygen_adapter: Optional[HeyGenAPIAdapter] = None):
        self.heygen = heygen_adapter or HeyGenAPIAdapter()
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

    # ==================== Zoom Integration (Placeholder) ====================

    async def connect_avatar_to_zoom(
        self,
        session_id: str,
        zoom_meeting_url: str,
        zoom_room_id: str
    ) -> Dict[str, Any]:
        """
        Connect HeyGen avatar to a Zoom breakout room

        This is a placeholder - actual implementation requires:
        1. Zoom Meeting SDK bot credentials
        2. WebRTC bridge between HeyGen and Zoom
        3. Virtual participant creation in Zoom

        Args:
            session_id: HeyGen avatar session ID
            zoom_meeting_url: Zoom meeting join URL
            zoom_room_id: Specific breakout room ID

        Returns:
            Connection status
        """
        logger.warning(
            "Avatar-to-Zoom connection not yet implemented. "
            "Requires Zoom Meeting SDK bot integration."
        )

        # TODO: Implement Zoom SDK bot
        # 1. Create Zoom SDK bot credentials
        # 2. Join Zoom meeting as virtual participant
        # 3. Route audio: Zoom -> HeyGen (student speaks)
        # 4. Route audio: HeyGen -> Zoom (avatar responds)
        # 5. Assign bot to specific breakout room

        return {
            "status": "pending_implementation",
            "session_id": session_id,
            "zoom_meeting_url": zoom_meeting_url,
            "zoom_room_id": zoom_room_id,
            "message": "Zoom integration requires Meeting SDK bot implementation"
        }

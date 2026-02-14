"""
Zoom Manager Service
Handles Zoom meeting and breakout room operations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from integrations.zoom_sdk_adapter import ZoomAPIAdapter
from models.models import Session, Student, BreakoutRoom

logger = logging.getLogger(__name__)


class ZoomManager:
    """
    High-level service for managing Zoom meetings and breakout rooms
    """

    def __init__(self, zoom_adapter: Optional[ZoomAPIAdapter] = None):
        self.zoom = zoom_adapter or ZoomAPIAdapter()

    async def validate_connection(self) -> bool:
        """
        Test Zoom API connection and credentials
        """
        return await self.zoom.validate_credentials()

    async def create_meeting_with_breakout_rooms(
        self,
        host_user_id: str,
        topic: str,
        students: List[Student],
        duration: int = 60,
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a Zoom meeting with pre-configured breakout rooms

        Args:
            host_user_id: Zoom user ID of the professor/host
            topic: Meeting topic
            students: List of Student objects
            duration: Meeting duration in minutes
            start_time: Scheduled start time (None for instant meeting)

        Returns:
            Dictionary with meeting details and breakout room assignments
        """
        try:
            # Step 1: Create the meeting
            logger.info(f"Creating Zoom meeting: {topic}")
            meeting = await self.zoom.create_meeting(
                user_id=host_user_id,
                topic=topic,
                start_time=start_time,
                duration=duration,
                settings={
                    "host_video": True,
                    "participant_video": True,
                    "join_before_host": True,
                    "mute_upon_entry": False,
                    "waiting_room": False,
                    "breakout_room": {
                        "enable": True
                    }
                }
            )

            meeting_id = str(meeting["id"])
            join_url = meeting["join_url"]

            logger.info(f"Meeting created: {meeting_id}")

            # Step 2: Create breakout rooms (one per student)
            rooms = []
            for idx, student in enumerate(students):
                room_name = f"Room {idx + 1} - {student.name}"
                # Note: Zoom API expects email addresses for participant assignment
                rooms.append({
                    "name": room_name,
                    "participants": [student.email] if student.email else []
                })

            if rooms:
                logger.info(f"Creating {len(rooms)} breakout rooms")
                breakout_result = await self.zoom.create_breakout_rooms(
                    meeting_id=meeting_id,
                    rooms=rooms
                )

                logger.info(f"Breakout rooms created successfully")
            else:
                logger.warning("No students provided, skipping breakout room creation")
                breakout_result = {"rooms": []}

            return {
                "meeting_id": meeting_id,
                "join_url": join_url,
                "start_url": meeting.get("start_url"),
                "topic": topic,
                "duration": duration,
                "breakout_rooms": breakout_result.get("rooms", []),
                "status": "created"
            }

        except Exception as e:
            logger.error(f"Failed to create meeting with breakout rooms: {e}")
            raise

    async def get_meeting_details(self, meeting_id: str) -> Dict[str, Any]:
        """
        Get details of a Zoom meeting
        """
        try:
            meeting = await self.zoom.get_meeting(meeting_id)
            return {
                "meeting_id": meeting["id"],
                "topic": meeting["topic"],
                "status": meeting.get("status"),
                "start_time": meeting.get("start_time"),
                "join_url": meeting["join_url"]
            }
        except Exception as e:
            logger.error(f"Failed to get meeting details: {e}")
            raise

    async def get_breakout_room_status(self, meeting_id: str) -> Dict[str, Any]:
        """
        Get status of breakout rooms for a meeting
        """
        try:
            rooms = await self.zoom.get_breakout_rooms(meeting_id)
            return {
                "meeting_id": meeting_id,
                "rooms": rooms.get("rooms", []),
                "total_rooms": len(rooms.get("rooms", []))
            }
        except Exception as e:
            logger.error(f"Failed to get breakout room status: {e}")
            raise

    async def assign_participants_to_rooms(
        self,
        meeting_id: str,
        assignments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update breakout room participant assignments

        Args:
            meeting_id: Zoom meeting ID
            assignments: List of room assignments
                [
                    {"name": "Room 1", "participants": ["user@email.com"]},
                    ...
                ]
        """
        try:
            result = await self.zoom.update_breakout_rooms(meeting_id, assignments)
            logger.info(f"Updated breakout room assignments for meeting {meeting_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to assign participants: {e}")
            raise

    async def delete_meeting(self, meeting_id: str) -> bool:
        """
        Delete a Zoom meeting
        """
        try:
            await self.zoom.delete_meeting(meeting_id)
            logger.info(f"Deleted meeting: {meeting_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete meeting: {e}")
            return False

    async def get_active_participants(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get list of participants currently in the meeting
        Note: Only works for live meetings
        """
        try:
            result = await self.zoom.get_meeting_participants(meeting_id)
            participants = result.get("participants", [])
            logger.info(f"Found {len(participants)} participants in meeting {meeting_id}")
            return participants
        except Exception as e:
            logger.error(f"Failed to get participants: {e}")
            return []

    async def open_breakout_rooms(self, meeting_id: str) -> bool:
        """
        Open breakout rooms for a meeting
        Note: This requires the Zoom SDK Bot or host action
        The REST API doesn't support this directly
        """
        logger.warning(
            "Opening breakout rooms programmatically requires Zoom SDK Bot. "
            "The host must click 'Open All Rooms' manually or we need to implement a bot."
        )
        # TODO: Implement using Zoom SDK Bot in future phase
        return False

    async def close_breakout_rooms(self, meeting_id: str) -> bool:
        """
        Close breakout rooms
        Note: Also requires SDK Bot or host action
        """
        logger.warning("Closing breakout rooms requires Zoom SDK Bot or host action")
        # TODO: Implement using Zoom SDK Bot in future phase
        return False

    # ==================== Helper Methods ====================

    def generate_room_assignments(
        self,
        students: List[Student],
        rooms_per_student: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate breakout room assignments

        Args:
            students: List of students
            rooms_per_student: If True, create one room per student.
                              If False, implement grouping logic

        Returns:
            List of room configurations
        """
        if rooms_per_student:
            # One student per room (for AI avatar pairing)
            return [
                {
                    "name": f"Room {idx + 1} - {student.name}",
                    "participants": [student.email] if student.email else []
                }
                for idx, student in enumerate(students)
            ]
        else:
            # TODO: Implement grouping logic for multiple students per room
            raise NotImplementedError("Group assignments not yet implemented")

    async def get_join_url_for_room(
        self,
        meeting_id: str,
        room_id: str
    ) -> Optional[str]:
        """
        Get join URL for a specific breakout room
        Note: Zoom API doesn't provide direct room join URLs
        Participants are moved by host or SDK
        """
        logger.info(
            "Zoom doesn't provide direct breakout room URLs. "
            "Participants join the main meeting and are assigned to rooms."
        )
        return None

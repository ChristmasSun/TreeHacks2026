"""
RTMS Transcription Service
Receives live transcription from Zoom RTMS and feeds to HeyGen avatars
"""
import logging
from typing import Dict, Any, Optional, Callable
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class RTMSTranscriptionService:
    """
    Service to receive and process RTMS transcription data
    Manages the flow: RTMS transcript -> Context buffer -> HeyGen avatar
    """

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # meeting_uuid -> session_data
        self.transcript_buffers: Dict[str, list] = {}  # meeting_uuid -> transcript chunks
        self.context_update_callbacks: Dict[str, Callable] = {}  # meeting_uuid -> callback function

    def start_session(
        self,
        meeting_uuid: str,
        rtms_stream_id: str,
        room_id: Optional[int] = None,
        on_transcript_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Start tracking RTMS session for a meeting

        Args:
            meeting_uuid: Zoom meeting UUID
            rtms_stream_id: RTMS stream identifier
            room_id: Associated breakout room ID (optional)
            on_transcript_callback: Async function to call with transcript updates

        Returns:
            Session details
        """
        logger.info(f"Starting RTMS transcription session for meeting {meeting_uuid}")

        self.active_sessions[meeting_uuid] = {
            "meeting_uuid": meeting_uuid,
            "rtms_stream_id": rtms_stream_id,
            "room_id": room_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "active"
        }

        self.transcript_buffers[meeting_uuid] = []

        if on_transcript_callback:
            self.context_update_callbacks[meeting_uuid] = on_transcript_callback

        return self.active_sessions[meeting_uuid]

    async def process_transcript_chunk(
        self,
        meeting_uuid: str,
        speaker_name: str,
        text: str,
        timestamp: Optional[str] = None
    ) -> None:
        """
        Process incoming transcript chunk from RTMS

        Args:
            meeting_uuid: Meeting identifier
            speaker_name: Name of the speaker
            text: Transcribed text
            timestamp: Timestamp of the transcript
        """
        if meeting_uuid not in self.active_sessions:
            logger.warning(f"Received transcript for unknown session: {meeting_uuid}")
            return

        # Store in buffer
        transcript_entry = {
            "speaker": speaker_name,
            "text": text,
            "timestamp": timestamp or datetime.utcnow().isoformat()
        }

        self.transcript_buffers[meeting_uuid].append(transcript_entry)
        logger.debug(f"[{meeting_uuid}] {speaker_name}: {text}")

        # Trigger callback if registered
        if meeting_uuid in self.context_update_callbacks:
            callback = self.context_update_callbacks[meeting_uuid]
            try:
                await callback(speaker_name, text, transcript_entry)
            except Exception as e:
                logger.error(f"Error in transcript callback for {meeting_uuid}: {e}")

    def get_session_context(
        self,
        meeting_uuid: str,
        max_entries: int = 10
    ) -> str:
        """
        Get formatted conversation context for a session

        Args:
            meeting_uuid: Meeting identifier
            max_entries: Maximum number of recent entries to include

        Returns:
            Formatted context string
        """
        if meeting_uuid not in self.transcript_buffers:
            return ""

        recent_transcripts = self.transcript_buffers[meeting_uuid][-max_entries:]

        context_lines = []
        for entry in recent_transcripts:
            context_lines.append(f"{entry['speaker']}: {entry['text']}")

        return "\n".join(context_lines)

    def get_recent_transcripts(
        self,
        meeting_uuid: str,
        limit: int = 5
    ) -> list:
        """
        Get recent transcript entries

        Args:
            meeting_uuid: Meeting identifier
            limit: Number of recent entries

        Returns:
            List of transcript entries
        """
        if meeting_uuid not in self.transcript_buffers:
            return []

        return self.transcript_buffers[meeting_uuid][-limit:]

    def stop_session(self, meeting_uuid: str) -> bool:
        """
        Stop tracking RTMS session

        Args:
            meeting_uuid: Meeting identifier

        Returns:
            Success status
        """
        if meeting_uuid not in self.active_sessions:
            logger.warning(f"Attempted to stop unknown session: {meeting_uuid}")
            return False

        logger.info(f"Stopping RTMS transcription session for meeting {meeting_uuid}")

        # Clean up
        self.active_sessions[meeting_uuid]["status"] = "stopped"
        self.active_sessions[meeting_uuid]["stopped_at"] = datetime.utcnow().isoformat()

        # Remove from active tracking (but keep session record)
        if meeting_uuid in self.context_update_callbacks:
            del self.context_update_callbacks[meeting_uuid]

        return True

    def get_session_stats(self, meeting_uuid: str) -> Dict[str, Any]:
        """
        Get statistics for a session

        Args:
            meeting_uuid: Meeting identifier

        Returns:
            Session statistics
        """
        if meeting_uuid not in self.active_sessions:
            return {"error": "Session not found"}

        transcript_count = len(self.transcript_buffers.get(meeting_uuid, []))

        return {
            "meeting_uuid": meeting_uuid,
            "status": self.active_sessions[meeting_uuid].get("status"),
            "transcript_count": transcript_count,
            "started_at": self.active_sessions[meeting_uuid].get("started_at"),
            "room_id": self.active_sessions[meeting_uuid].get("room_id")
        }

    def clear_old_data(self, meeting_uuid: str) -> None:
        """
        Clear transcript buffer and session data for completed session

        Args:
            meeting_uuid: Meeting identifier
        """
        if meeting_uuid in self.transcript_buffers:
            del self.transcript_buffers[meeting_uuid]

        if meeting_uuid in self.active_sessions:
            del self.active_sessions[meeting_uuid]

        logger.info(f"Cleared data for session {meeting_uuid}")

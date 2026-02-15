"""
Session Orchestrator (Simplified)
Manages breakout sessions without Zoom meeting creation.
Breakout rooms are Electron-side only — professor triggers, students get HeyGen avatar windows.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionOrchestrator:
    """
    Simplified orchestrator for Electron-side breakout rooms.
    No Zoom meeting creation — everyone stays in the main Zoom meeting (for show).
    """

    def __init__(self, on_transcript_callback: Optional[Any] = None):
        self.on_transcript_callback = on_transcript_callback
        self.active_session: Optional[Dict] = None

    async def start_session(self, topic: str = "AI Tutoring Session") -> Dict[str, Any]:
        """Start a new tutoring session (Electron-side breakout)."""
        self.active_session = {
            "session_id": int(datetime.utcnow().timestamp()),
            "topic": topic,
            "status": "active",
            "start_time": datetime.utcnow().isoformat(),
            "students": [],
        }
        logger.info(f"Session started: {self.active_session['session_id']}")
        return self.active_session

    async def end_session(self) -> Dict[str, Any]:
        """End the current session."""
        if not self.active_session:
            return {"status": "no_session"}
        self.active_session["status"] = "completed"
        self.active_session["end_time"] = datetime.utcnow().isoformat()
        result = self.active_session
        self.active_session = None
        logger.info(f"Session ended: {result['session_id']}")
        return result

    def get_session_status(self) -> Optional[Dict[str, Any]]:
        """Get current session status."""
        return self.active_session

"""
HeyGen Interactive Avatar API adapter
Manages avatar sessions and WebRTC streaming
"""
import os
import httpx
from typing import Optional, Dict, Any, List
import logging
import json
import asyncio

logger = logging.getLogger(__name__)


class HeyGenAPIAdapter:
    """
    Wrapper for HeyGen Interactive Avatar API v2
    Handles authentication and avatar session management
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com/v1"  # v1 for streaming APIs
        self.streaming_base_url = "https://api.heygen.com/v1/streaming"

        if not self.api_key:
            logger.warning("HeyGen API key not configured")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to HeyGen API
        """
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

    # ==================== Interactive Avatar Management ====================

    async def create_streaming_avatar(
        self,
        avatar_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        quality: str = "high"
    ) -> Dict[str, Any]:
        """
        Create a new streaming avatar session

        Args:
            avatar_id: HeyGen avatar ID (use default if not provided)
            voice_id: Voice ID for the avatar
            quality: Video quality ("low", "medium", "high")

        Returns:
            Session details including session_id and access_token
        """
        data = {
            "quality": quality,
        }

        if avatar_id:
            data["avatar_id"] = avatar_id
        if voice_id:
            data["voice_id"] = voice_id

        result = await self._make_request("POST", "/streaming.new", data=data)
        session_data = result.get("data", {})
        
        # Log full response for debugging
        logger.info(f"HeyGen streaming.new response: {session_data}")
        
        # Normalize field names - HeyGen uses different field names
        normalized = {
            "session_id": session_data.get("session_id"),
            "url": session_data.get("url") or session_data.get("livekit_url") or session_data.get("server_url"),
            "access_token": session_data.get("access_token") or session_data.get("token"),
            "ice_servers": session_data.get("ice_servers", []),
            "ice_servers2": session_data.get("ice_servers2", []),
        }
        
        logger.info(f"Created streaming avatar session: {normalized.get('session_id')}, url: {normalized.get('url')}")
        return normalized

    async def start_avatar_session(
        self,
        session_id: str,
        sdp_offer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start WebRTC session for streaming avatar

        Args:
            session_id: Avatar session ID from create_streaming_avatar
            sdp_offer: WebRTC SDP offer (optional for server-initiated)

        Returns:
            SDP answer for WebRTC connection
        """
        data = {
            "session_id": session_id,
        }

        if sdp_offer:
            data["sdp"] = {
                "type": "offer",
                "sdp": sdp_offer
            }

        result = await self._make_request("POST", "/streaming.start", data=data)
        session_data = result.get("data", {})
        
        # Log full response for debugging
        logger.info(f"HeyGen streaming.start response: {session_data}")
        
        # Normalize field names
        normalized = {
            "url": session_data.get("url") or session_data.get("livekit_url") or session_data.get("server_url"),
            "access_token": session_data.get("access_token") or session_data.get("token"),
            "sdp": session_data.get("sdp"),
        }
        
        logger.info(f"Started avatar session: {session_id}, url: {normalized.get('url')}")
        return normalized

    async def send_message_to_avatar(
        self,
        session_id: str,
        message: str,
        task_type: str = "talk",
        task_mode: str = "sync"
    ) -> Dict[str, Any]:
        """
        Send a message/task to the streaming avatar

        Args:
            session_id: Avatar session ID
            message: Text for avatar to speak
            task_type: "talk" (speak text) or "repeat" (echo)
            task_mode: "sync" (wait for completion) or "async" (return immediately)

        Returns:
            Task result including task_id
        """
        data = {
            "session_id": session_id,
            "text": message,
            "task_type": task_type,
            "task_mode": task_mode
        }

        result = await self._make_request("POST", "/streaming.task", data=data)
        logger.debug(f"Sent message to avatar {session_id}: {message[:50]}...")
        return result.get("data", {})

    async def interrupt_avatar(self, session_id: str) -> Dict[str, Any]:
        """
        Interrupt avatar while speaking
        """
        data = {"session_id": session_id}
        result = await self._make_request("POST", "/streaming.interrupt", data=data)
        logger.info(f"Interrupted avatar: {session_id}")
        return result.get("data", {})

    async def get_ice_servers(self, session_id: str) -> Dict[str, Any]:
        """
        Get ICE servers for WebRTC connection
        """
        result = await self._make_request(
            "GET",
            "/streaming.ice",
            params={"session_id": session_id}
        )
        return result.get("data", {})

    async def stop_avatar_session(self, session_id: str) -> Dict[str, Any]:
        """
        Stop and cleanup streaming avatar session
        """
        data = {"session_id": session_id}
        result = await self._make_request("POST", "/streaming.stop", data=data)
        logger.info(f"Stopped avatar session: {session_id}")
        return result.get("data", {})

    # ==================== Avatar Configuration ====================

    async def list_avatars(self) -> List[Dict[str, Any]]:
        """
        Get list of available avatars
        """
        result = await self._make_request("GET", "/avatars")
        return result.get("data", {}).get("avatars", [])

    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices
        """
        result = await self._make_request("GET", "/voices")
        return result.get("data", {}).get("voices", [])

    # ==================== Knowledge Base (for Context) ====================

    async def create_knowledge_base(
        self,
        name: str,
        files: Optional[List[str]] = None,
        urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a knowledge base for avatar context

        Args:
            name: Knowledge base name
            files: List of file paths to upload
            urls: List of URLs to scrape

        Returns:
            Knowledge base details including kb_id
        """
        data = {
            "name": name,
            "files": files or [],
            "urls": urls or []
        }

        result = await self._make_request("POST", "/knowledge-bases", data=data)
        logger.info(f"Created knowledge base: {result.get('data', {}).get('kb_id')}")
        return result.get("data", {})

    async def add_context_to_session(
        self,
        session_id: str,
        kb_id: Optional[str] = None,
        context_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add context/knowledge to an avatar session

        Args:
            session_id: Avatar session ID
            kb_id: Knowledge base ID
            context_text: Direct text context

        Returns:
            Updated session details
        """
        data = {"session_id": session_id}

        if kb_id:
            data["knowledge_base_id"] = kb_id
        if context_text:
            data["context"] = context_text

        result = await self._make_request("POST", "/streaming.context", data=data)
        logger.info(f"Added context to avatar session: {session_id}")
        return result.get("data", {})

    # ==================== Utility Methods ====================

    async def validate_credentials(self) -> bool:
        """
        Validate HeyGen API credentials
        """
        try:
            await self.list_avatars()
            logger.info("HeyGen credentials validated successfully")
            return True
        except Exception as e:
            logger.error(f"HeyGen credentials validation failed: {e}")
            return False

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current status of avatar session
        """
        result = await self._make_request(
            "GET",
            "/streaming.status",
            params={"session_id": session_id}
        )
        return result.get("data", {})

    # ==================== Zoom Integration Helpers ====================

    async def create_avatar_for_zoom(
        self,
        professor_name: str,
        avatar_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and configure avatar session for Zoom integration

        Args:
            professor_name: Professor's name for avatar configuration
            avatar_id: Specific avatar to use
            voice_id: Specific voice to use
            context: Course context/knowledge

        Returns:
            Complete session details ready for Zoom integration
        """
        # Step 1: Create streaming session
        session_data = await self.create_streaming_avatar(
            avatar_id=avatar_id,
            voice_id=voice_id,
            quality="high"
        )

        session_id = session_data.get("session_id")
        if not session_id:
            raise ValueError("Failed to create avatar session")

        # Step 2: Add context if provided
        if context:
            await self.add_context_to_session(
                session_id=session_id,
                context_text=context
            )

        # Step 3: Start the session
        start_result = await self.start_avatar_session(session_id)

        return {
            "session_id": session_id,
            "access_token": session_data.get("access_token"),
            "sdp_answer": start_result.get("sdp"),
            "ice_servers": start_result.get("ice_servers", []),
            "ready": True
        }

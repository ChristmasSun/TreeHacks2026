"""
Zoom API adapter for meeting and breakout room management
Uses Zoom REST API v2
"""
import os
import httpx
import base64
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ZoomAPIAdapter:
    """
    Wrapper for Zoom REST API v2
    Handles authentication and common operations
    """

    def __init__(
        self,
        account_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        self.account_id = account_id or os.getenv("ZOOM_ACCOUNT_ID")
        self.client_id = client_id or os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ZOOM_CLIENT_SECRET")

        self.base_url = "https://api.zoom.us/v2"
        self.token_url = "https://zoom.us/oauth/token"
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        if not all([self.account_id, self.client_id, self.client_secret]):
            logger.warning("Zoom credentials not fully configured")

    async def _get_access_token(self) -> str:
        """
        Get Server-to-Server OAuth access token
        """
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token

        # Request new token
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers=headers,
                data=data
            )
            response.raise_for_status()
            token_data = response.json()

        self.access_token = token_data["access_token"]
        # Set expiration (default 1 hour, refresh 5 min early)
        expires_in = token_data.get("expires_in", 3600)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)

        logger.info("Zoom access token obtained")
        return self.access_token

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Zoom API
        """
        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            # Some endpoints return no content
            if response.status_code == 204:
                return {"status": "success"}

            return response.json()

    # ==================== Meeting Management ====================

    async def create_meeting(
        self,
        user_id: str,
        topic: str,
        start_time: Optional[datetime] = None,
        duration: int = 60,
        settings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a Zoom meeting

        Args:
            user_id: Zoom user ID or email
            topic: Meeting topic
            start_time: Meeting start time (None for instant meeting)
            duration: Meeting duration in minutes
            settings: Additional meeting settings

        Returns:
            Meeting details including meeting_id and join_url
        """
        data = {
            "topic": topic,
            "type": 2 if start_time else 1,  # 1=instant, 2=scheduled
            "duration": duration,
            "settings": settings or {
                "host_video": True,
                "participant_video": True,
                "join_before_host": True,
                "mute_upon_entry": False,
                "breakout_room": {
                    "enable": True
                }
            }
        }

        if start_time:
            data["start_time"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        result = await self._make_request("POST", f"/users/{user_id}/meetings", data=data)
        logger.info(f"Created Zoom meeting: {result.get('id')}")
        return result

    async def get_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Get meeting details"""
        return await self._make_request("GET", f"/meetings/{meeting_id}")

    async def delete_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Delete a meeting"""
        return await self._make_request("DELETE", f"/meetings/{meeting_id}")

    # ==================== Breakout Room Management ====================

    async def create_breakout_rooms(
        self,
        meeting_id: str,
        rooms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create breakout rooms for a meeting

        Args:
            meeting_id: Zoom meeting ID
            rooms: List of room configurations
                [
                    {"name": "Room 1", "participants": ["user@email.com"]},
                    {"name": "Room 2", "participants": ["user2@email.com"]}
                ]

        Returns:
            Created breakout rooms details
        """
        data = {"rooms": rooms}

        result = await self._make_request(
            "POST",
            f"/meetings/{meeting_id}/breakout_rooms",
            data=data
        )
        logger.info(f"Created {len(rooms)} breakout rooms for meeting {meeting_id}")
        return result

    async def get_breakout_rooms(self, meeting_id: str) -> Dict[str, Any]:
        """Get breakout rooms for a meeting"""
        return await self._make_request("GET", f"/meetings/{meeting_id}/breakout_rooms")

    async def update_breakout_rooms(
        self,
        meeting_id: str,
        rooms: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update breakout room assignments"""
        data = {"rooms": rooms}
        return await self._make_request(
            "PATCH",
            f"/meetings/{meeting_id}/breakout_rooms",
            data=data
        )

    async def delete_breakout_rooms(self, meeting_id: str) -> Dict[str, Any]:
        """Delete all breakout rooms from a meeting"""
        return await self._make_request("DELETE", f"/meetings/{meeting_id}/breakout_rooms")

    # ==================== Participant Management ====================

    async def get_meeting_participants(
        self,
        meeting_id: str,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """
        Get live meeting participants
        Note: Only works for meetings that have already started
        """
        params = {"page_size": page_size}
        return await self._make_request(
            "GET",
            f"/metrics/meetings/{meeting_id}/participants",
            params=params
        )

    async def add_meeting_registrant(
        self,
        meeting_id: str,
        email: str,
        first_name: str,
        last_name: str
    ) -> Dict[str, Any]:
        """Add a registrant to a meeting"""
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        }
        return await self._make_request(
            "POST",
            f"/meetings/{meeting_id}/registrants",
            data=data
        )

    # ==================== User Management ====================

    async def get_users(self, page_size: int = 30) -> Dict[str, Any]:
        """Get list of users in the account"""
        params = {"page_size": page_size}
        return await self._make_request("GET", "/users", params=params)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        return await self._make_request("GET", f"/users/{user_id}")

    # ==================== Recording Management ====================

    async def get_meeting_recordings(self, meeting_id: str) -> Dict[str, Any]:
        """Get cloud recordings for a meeting"""
        return await self._make_request("GET", f"/meetings/{meeting_id}/recordings")

    # ==================== Utility Methods ====================

    async def validate_credentials(self) -> bool:
        """
        Validate that Zoom credentials are working
        """
        try:
            await self._get_access_token()
            await self.get_users(page_size=1)
            logger.info("Zoom credentials validated successfully")
            return True
        except Exception as e:
            logger.error(f"Zoom credentials validation failed: {e}")
            return False

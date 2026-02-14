"""
Zoom Bot Service Client
Communicates with Node.js Zoom Bot Service via HTTP API
"""
import httpx
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ZoomBotServiceClient:
    """Client for communicating with Node.js Zoom Bot Service"""

    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def health_check(self) -> Dict[str, Any]:
        """Check if bot service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Bot service health check failed: {e}")
            raise

    async def create_bot(
        self,
        meeting_number: str,
        bot_name: str,
        room_id: int,
        passcode: Optional[str] = None,
        heygen_session_id: Optional[str] = None
    ) -> str:
        """
        Create a bot and join Zoom meeting

        Args:
            meeting_number: Zoom meeting number
            bot_name: Display name for the bot (e.g., "AI Professor - Alice")
            room_id: Breakout room ID
            passcode: Meeting passcode (optional)
            heygen_session_id: HeyGen avatar session ID (optional)

        Returns:
            bot_id: UUID of created bot
        """
        try:
            payload = {
                "meeting_number": meeting_number,
                "bot_name": bot_name,
                "room_id": room_id,
            }

            if passcode:
                payload["passcode"] = passcode
            if heygen_session_id:
                payload["heygen_session_id"] = heygen_session_id

            response = await self.client.post(
                f"{self.base_url}/bots/create",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Bot created: {result['bot_id']}")
            return result["bot_id"]

        except Exception as e:
            logger.error(f"Failed to create bot: {e}")
            raise

    async def get_all_bots(self) -> List[Dict[str, Any]]:
        """Get list of all active bots"""
        try:
            response = await self.client.get(f"{self.base_url}/bots")
            response.raise_for_status()
            return response.json()["bots"]
        except Exception as e:
            logger.error(f"Failed to get bots: {e}")
            raise

    async def get_bot_info(self, bot_id: str) -> Dict[str, Any]:
        """Get information about a specific bot"""
        try:
            response = await self.client.get(f"{self.base_url}/bots/{bot_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            raise

    async def move_bot_to_breakout_room(
        self,
        bot_id: str,
        breakout_room_id: str
    ) -> None:
        """Move bot to a specific breakout room"""
        try:
            response = await self.client.post(
                f"{self.base_url}/bots/{bot_id}/join-breakout-room",
                json={"breakout_room_id": breakout_room_id}
            )
            response.raise_for_status()
            logger.info(f"Bot {bot_id} moved to room {breakout_room_id}")
        except Exception as e:
            logger.error(f"Failed to move bot to breakout room: {e}")
            raise

    async def play_audio(
        self,
        bot_id: str,
        audio_data: bytes
    ) -> None:
        """
        Play audio through bot (HeyGen avatar response)

        Args:
            bot_id: Bot UUID
            audio_data: Raw audio bytes (will be base64 encoded)
        """
        try:
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')

            response = await self.client.post(
                f"{self.base_url}/bots/{bot_id}/play-audio",
                json={"audio_data": audio_b64}
            )
            response.raise_for_status()
            logger.info(f"Audio sent to bot {bot_id}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            raise

    async def remove_bot(self, bot_id: str) -> None:
        """Stop and remove a bot"""
        try:
            response = await self.client.delete(f"{self.base_url}/bots/{bot_id}")
            response.raise_for_status()
            logger.info(f"Bot {bot_id} removed")
        except Exception as e:
            logger.error(f"Failed to remove bot: {e}")
            raise

    async def remove_all_bots(self) -> None:
        """Remove all bots (cleanup)"""
        try:
            response = await self.client.delete(f"{self.base_url}/bots")
            response.raise_for_status()
            logger.info("All bots removed")
        except Exception as e:
            logger.error(f"Failed to remove all bots: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get bot service statistics"""
        try:
            response = await self.client.get(f"{self.base_url}/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

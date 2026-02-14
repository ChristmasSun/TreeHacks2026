"""
Transcription Service
Coordinates real-time transcription for breakout room conversations
Integrates with HeyGen audio streams and Deepgram API
"""
import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.models import Transcript, BreakoutRoom

# Make deepgram optional (requires Python 3.10+)
try:
    from integrations.deepgram_adapter import DeepgramAdapter, create_deepgram_adapter
    DEEPGRAM_AVAILABLE = True
except (ImportError, SyntaxError):
    DeepgramAdapter = None
    create_deepgram_adapter = None
    DEEPGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Manages real-time transcription for all active breakout rooms

    Features:
    - Per-room transcription streams
    - Integration with HeyGen audio pipeline
    - Real-time transcript saving to database
    - WebSocket forwarding to frontend
    - Speaker diarization (student vs bot)
    """

    def __init__(
        self,
        deepgram_api_key: Optional[str] = None,
        on_transcript_callback: Optional[Callable] = None
    ):
        """
        Initialize transcription service

        Args:
            deepgram_api_key: Deepgram API key
            on_transcript_callback: Callback for real-time transcript forwarding
        """
        # Active transcription adapters per room
        self.active_streams: Dict[int, Any] = {}  # DeepgramAdapter when available

        # Deepgram API key
        self.deepgram_api_key = deepgram_api_key

        # Callback for real-time transcript forwarding (to WebSocket)
        self.on_transcript_callback = on_transcript_callback

        if not DEEPGRAM_AVAILABLE:
            logger.warning("Deepgram not available (requires Python 3.10+). Transcription disabled.")
        
        logger.info("TranscriptionService initialized")

    async def start_room_transcription(
        self,
        db: AsyncSession,
        room_id: int,
        language: str = "en-US"
    ) -> bool:
        """
        Start transcription for a specific breakout room

        This should be called when:
        1. HeyGen avatar joins the breakout room
        2. Audio pipeline is established

        Args:
            db: Database session
            room_id: Breakout room ID
            language: Language code for transcription

        Returns:
            True if transcription started successfully
        """
        if not DEEPGRAM_AVAILABLE:
            logger.warning(f"Deepgram not available, transcription disabled for room {room_id}")
            return False
            
        try:
            # Check if room exists
            room = await db.get(BreakoutRoom, room_id)
            if not room:
                logger.error(f"Room {room_id} not found")
                return False

            # Check if already transcribing
            if room_id in self.active_streams:
                logger.warning(f"Transcription already active for room {room_id}")
                return True

            # Create Deepgram adapter for this room
            adapter = create_deepgram_adapter(self.deepgram_api_key)
            if not adapter:
                logger.error(f"Failed to create Deepgram adapter for room {room_id}")
                return False

            # Set up transcript callback
            adapter.on_transcript = lambda transcript: asyncio.create_task(
                self._handle_transcript(db, transcript)
            )

            adapter.on_error = lambda error: asyncio.create_task(
                self._handle_error(error)
            )

            # Start the stream
            success = await adapter.start_stream(
                room_id=room_id,
                language=language,
                enable_speaker_diarization=True,
                enable_punctuation=True,
                enable_interim_results=True
            )

            if success:
                self.active_streams[room_id] = adapter
                logger.info(f"Started transcription for room {room_id}")
                return True
            else:
                logger.error(f"Failed to start Deepgram stream for room {room_id}")
                return False

        except Exception as e:
            logger.error(f"Error starting transcription for room {room_id}: {e}")
            return False

    async def process_audio_chunk(
        self,
        room_id: int,
        audio_data: bytes
    ) -> bool:
        """
        Process audio chunk from HeyGen avatar

        This receives audio from the HeyGen audio pipeline and forwards it to Deepgram

        Args:
            room_id: Breakout room ID
            audio_data: Raw PCM audio data (linear16, 16kHz, mono)

        Returns:
            True if audio processed successfully
        """
        try:
            # Get the active stream for this room
            adapter = self.active_streams.get(room_id)
            if not adapter:
                logger.warning(
                    f"No active transcription stream for room {room_id}. "
                    "Start transcription first."
                )
                return False

            # Send audio to Deepgram
            return await adapter.send_audio(audio_data)

        except Exception as e:
            logger.error(f"Error processing audio for room {room_id}: {e}")
            return False

    async def stop_room_transcription(
        self,
        room_id: int
    ) -> bool:
        """
        Stop transcription for a specific breakout room

        Args:
            room_id: Breakout room ID

        Returns:
            True if transcription stopped successfully
        """
        try:
            adapter = self.active_streams.get(room_id)
            if not adapter:
                logger.warning(f"No active transcription for room {room_id}")
                return False

            # Stop the stream
            await adapter.stop_stream()

            # Remove from active streams
            del self.active_streams[room_id]

            logger.info(f"Stopped transcription for room {room_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping transcription for room {room_id}: {e}")
            return False

    async def stop_all_transcriptions(self):
        """
        Stop all active transcription streams
        Called when session ends
        """
        try:
            room_ids = list(self.active_streams.keys())
            for room_id in room_ids:
                await self.stop_room_transcription(room_id)

            logger.info("Stopped all transcription streams")

        except Exception as e:
            logger.error(f"Error stopping all transcriptions: {e}")

    async def get_room_transcripts(
        self,
        db: AsyncSession,
        room_id: int,
        limit: int = 100
    ) -> list:
        """
        Get transcripts for a specific room

        Args:
            db: Database session
            room_id: Breakout room ID
            limit: Maximum number of transcripts to return

        Returns:
            List of transcript dictionaries
        """
        try:
            # Query transcripts for this room
            result = await db.execute(
                select(Transcript)
                .where(Transcript.room_id == room_id)
                .order_by(Transcript.timestamp.desc())
                .limit(limit)
            )
            transcripts = result.scalars().all()

            return [
                {
                    "id": t.id,
                    "speaker": t.speaker,
                    "text": t.text,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                    "confidence": t.confidence,
                    "metadata": t.metadata
                }
                for t in transcripts
            ]

        except Exception as e:
            logger.error(f"Error getting transcripts for room {room_id}: {e}")
            return []

    async def _handle_transcript(
        self,
        db: AsyncSession,
        transcript_data: Dict[str, Any]
    ):
        """
        Handle transcript from Deepgram

        Args:
            db: Database session
            transcript_data: Transcript data from Deepgram
        """
        try:
            # Only save final transcripts to database (not interim results)
            if not transcript_data.get("is_final", False):
                # Still forward interim results to frontend for real-time display
                if self.on_transcript_callback:
                    await self.on_transcript_callback(transcript_data)
                return

            room_id = transcript_data["room_id"]
            text = transcript_data["text"]
            speaker = transcript_data.get("speaker", "unknown")
            confidence = transcript_data.get("confidence", 0.0)
            metadata = transcript_data.get("metadata", {})

            # Save to database
            transcript = Transcript(
                room_id=room_id,
                speaker=speaker,
                text=text,
                confidence=confidence,
                metadata=metadata
            )
            db.add(transcript)
            await db.commit()
            await db.refresh(transcript)

            logger.info(
                f"Saved transcript for room {room_id}: "
                f"{speaker} - {text[:50]}..."
            )

            # Forward to frontend via WebSocket
            if self.on_transcript_callback:
                await self.on_transcript_callback({
                    **transcript_data,
                    "transcript_id": transcript.id,
                    "saved": True
                })

        except Exception as e:
            logger.error(f"Error handling transcript: {e}")
            await db.rollback()

    async def _handle_error(self, error_data: Dict[str, Any]):
        """
        Handle errors from Deepgram

        Args:
            error_data: Error data from Deepgram
        """
        room_id = error_data.get("room_id")
        error_msg = error_data.get("error")

        logger.error(f"Transcription error for room {room_id}: {error_msg}")

        # Optionally forward error to frontend
        if self.on_transcript_callback:
            await self.on_transcript_callback({
                "type": "error",
                "room_id": room_id,
                "error": error_msg
            })

    def get_active_room_count(self) -> int:
        """
        Get number of rooms with active transcription

        Returns:
            Number of active transcription streams
        """
        return len(self.active_streams)

    def is_room_active(self, room_id: int) -> bool:
        """
        Check if transcription is active for a room

        Args:
            room_id: Breakout room ID

        Returns:
            True if transcription is active
        """
        return room_id in self.active_streams

    async def validate_service(self) -> bool:
        """
        Validate that the transcription service is properly configured

        Returns:
            True if service is valid
        """
        try:
            # Create a test adapter to validate credentials
            adapter = create_deepgram_adapter(self.deepgram_api_key)
            if not adapter:
                return False

            return await adapter.validate_credentials()

        except Exception as e:
            logger.error(f"Error validating transcription service: {e}")
            return False


# Helper function to create singleton instance
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service(
    deepgram_api_key: Optional[str] = None,
    on_transcript_callback: Optional[Callable] = None
) -> TranscriptionService:
    """
    Get or create transcription service singleton

    Args:
        deepgram_api_key: Deepgram API key
        on_transcript_callback: Callback for real-time transcripts

    Returns:
        TranscriptionService instance
    """
    global _transcription_service

    if _transcription_service is None:
        _transcription_service = TranscriptionService(
            deepgram_api_key=deepgram_api_key,
            on_transcript_callback=on_transcript_callback
        )

    return _transcription_service

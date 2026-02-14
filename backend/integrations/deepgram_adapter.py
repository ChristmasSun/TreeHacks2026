"""
Deepgram API Adapter
Real-time audio transcription using Deepgram's streaming API
"""
import os
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
import json
from datetime import datetime

try:
    from deepgram import (
        DeepgramClient,
        DeepgramClientOptions,
        LiveTranscriptionEvents,
        LiveOptions,
        Microphone
    )
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False
    logging.warning("Deepgram SDK not installed. Run: pip install deepgram-sdk")

logger = logging.getLogger(__name__)


class DeepgramAdapter:
    """
    Adapter for Deepgram real-time transcription API

    Features:
    - WebSocket streaming for real-time transcription
    - Speaker diarization (identify student vs bot)
    - Confidence scores
    - Punctuation and formatting
    - Multiple language support
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Deepgram adapter

        Args:
            api_key: Deepgram API key (defaults to DEEPGRAM_API_KEY env var)
        """
        if not DEEPGRAM_AVAILABLE:
            raise ImportError(
                "Deepgram SDK not installed. "
                "Install with: pip install deepgram-sdk"
            )

        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Deepgram API key not found. "
                "Set DEEPGRAM_API_KEY environment variable or pass api_key parameter"
            )

        # Initialize Deepgram client
        config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )
        self.client = DeepgramClient(self.api_key, config)

        # Connection state
        self.connection = None
        self.is_connected = False

        # Callbacks
        self.on_transcript: Optional[Callable] = None
        self.on_metadata: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    async def start_stream(
        self,
        room_id: int,
        language: str = "en-US",
        enable_speaker_diarization: bool = True,
        enable_punctuation: bool = True,
        enable_interim_results: bool = True
    ) -> bool:
        """
        Start real-time transcription stream

        Args:
            room_id: Breakout room ID (for tracking)
            language: Language code (en-US, es, fr, etc.)
            enable_speaker_diarization: Detect different speakers
            enable_punctuation: Add punctuation to transcripts
            enable_interim_results: Get partial results before final

        Returns:
            True if stream started successfully
        """
        try:
            # Configure transcription options
            options = LiveOptions(
                model="nova-2",  # Latest Deepgram model
                language=language,
                punctuate=enable_punctuation,
                interim_results=enable_interim_results,
                diarize=enable_speaker_diarization,
                smart_format=True,  # Improved formatting
                encoding="linear16",  # PCM audio format
                sample_rate=16000,  # 16kHz sample rate
                channels=1,  # Mono audio
            )

            # Create live transcription connection
            self.connection = self.client.listen.websocket.v("1")

            # Set up event handlers
            self.connection.on(
                LiveTranscriptionEvents.Transcript,
                lambda result: asyncio.create_task(
                    self._handle_transcript(room_id, result)
                )
            )

            self.connection.on(
                LiveTranscriptionEvents.Metadata,
                lambda metadata: asyncio.create_task(
                    self._handle_metadata(room_id, metadata)
                )
            )

            self.connection.on(
                LiveTranscriptionEvents.Error,
                lambda error: asyncio.create_task(
                    self._handle_error(room_id, error)
                )
            )

            # Start the connection
            if await self.connection.start(options):
                self.is_connected = True
                logger.info(f"Deepgram stream started for room {room_id}")
                return True
            else:
                logger.error(f"Failed to start Deepgram stream for room {room_id}")
                return False

        except Exception as e:
            logger.error(f"Error starting Deepgram stream for room {room_id}: {e}")
            return False

    async def send_audio(self, audio_data: bytes) -> bool:
        """
        Send audio data to Deepgram for transcription

        Args:
            audio_data: Raw PCM audio bytes (linear16, 16kHz, mono)

        Returns:
            True if audio sent successfully
        """
        try:
            if not self.is_connected or not self.connection:
                logger.warning("Cannot send audio - not connected to Deepgram")
                return False

            # Send audio chunk to Deepgram
            self.connection.send(audio_data)
            return True

        except Exception as e:
            logger.error(f"Error sending audio to Deepgram: {e}")
            return False

    async def stop_stream(self) -> bool:
        """
        Stop transcription stream

        Returns:
            True if stream stopped successfully
        """
        try:
            if self.connection:
                await self.connection.finish()
                self.is_connected = False
                logger.info("Deepgram stream stopped")
                return True
            return False

        except Exception as e:
            logger.error(f"Error stopping Deepgram stream: {e}")
            return False

    async def _handle_transcript(self, room_id: int, result: Any):
        """
        Handle transcript result from Deepgram

        Args:
            room_id: Breakout room ID
            result: Transcript result from Deepgram
        """
        try:
            # Extract transcript data
            transcript_data = result.to_dict()

            # Check if this is a final result
            is_final = transcript_data.get("is_final", False)

            # Get the transcript text
            channel = transcript_data.get("channel", {})
            alternatives = channel.get("alternatives", [])

            if not alternatives:
                return

            best_alternative = alternatives[0]
            text = best_alternative.get("transcript", "").strip()

            if not text:
                return

            # Extract confidence and speaker info
            confidence = best_alternative.get("confidence", 0.0)
            words = best_alternative.get("words", [])

            # Determine speaker (if diarization enabled)
            speaker = "unknown"
            if words and len(words) > 0:
                # Use the most common speaker in this segment
                speakers = [w.get("speaker", 0) for w in words if "speaker" in w]
                if speakers:
                    # Map speaker number to role (0=student, 1=bot, etc.)
                    speaker_num = max(set(speakers), key=speakers.count)
                    speaker = "student" if speaker_num == 0 else "bot"

            # Create transcript object
            transcript = {
                "room_id": room_id,
                "text": text,
                "speaker": speaker,
                "confidence": confidence,
                "is_final": is_final,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "duration": channel.get("duration", 0),
                    "words": len(words)
                }
            }

            # Call transcript callback if set
            if self.on_transcript:
                await self.on_transcript(transcript)

            # Log final transcripts
            if is_final:
                logger.info(
                    f"Room {room_id} - {speaker}: {text} "
                    f"(confidence: {confidence:.2f})"
                )

        except Exception as e:
            logger.error(f"Error handling transcript for room {room_id}: {e}")

    async def _handle_metadata(self, room_id: int, metadata: Any):
        """Handle metadata from Deepgram"""
        try:
            if self.on_metadata:
                await self.on_metadata({
                    "room_id": room_id,
                    "metadata": metadata.to_dict() if hasattr(metadata, 'to_dict') else metadata
                })
        except Exception as e:
            logger.error(f"Error handling metadata for room {room_id}: {e}")

    async def _handle_error(self, room_id: int, error: Any):
        """Handle errors from Deepgram"""
        try:
            error_msg = str(error)
            logger.error(f"Deepgram error for room {room_id}: {error_msg}")

            if self.on_error:
                await self.on_error({
                    "room_id": room_id,
                    "error": error_msg
                })
        except Exception as e:
            logger.error(f"Error handling error for room {room_id}: {e}")

    async def validate_credentials(self) -> bool:
        """
        Validate Deepgram API credentials

        Returns:
            True if credentials are valid
        """
        try:
            # Try to get account balance/info as a test
            # Note: This is a simple check - actual validation happens on first stream
            return bool(self.api_key and len(self.api_key) > 0)
        except Exception as e:
            logger.error(f"Error validating Deepgram credentials: {e}")
            return False


# Helper function to create adapter instance
def create_deepgram_adapter(api_key: Optional[str] = None) -> Optional[DeepgramAdapter]:
    """
    Create a Deepgram adapter instance

    Args:
        api_key: Optional API key (uses env var if not provided)

    Returns:
        DeepgramAdapter instance or None if SDK not available
    """
    try:
        return DeepgramAdapter(api_key)
    except ImportError:
        logger.error("Deepgram SDK not installed")
        return None
    except ValueError as e:
        logger.error(f"Failed to create Deepgram adapter: {e}")
        return None

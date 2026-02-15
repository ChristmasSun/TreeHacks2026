"""
Pocket TTS Service for real-time voice synthesis.
Pre-loads model at startup for low-latency generation.
"""
import asyncio
import logging
import os
import uuid

import scipy.io.wavfile
from pocket_tts import TTSModel

logger = logging.getLogger(__name__)

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)


class PocketTTSService:
    """Local TTS with voice cloning via Pocket TTS."""

    def __init__(self):
        self._model: TTSModel | None = None
        self._voice_state = None

    def load(self):
        """Pre-load model and voice state. Call once at startup."""
        logger.info("Loading Pocket TTS model...")
        self._model = TTSModel.load_model()

        voice_path = os.getenv("VOICE_SAMPLE_PATH")
        if voice_path and os.path.exists(voice_path):
            logger.info(f"Loading voice sample from: {voice_path}")
            self._voice_state = self._model.get_state_for_audio_prompt(voice_path)
        else:
            logger.info("No VOICE_SAMPLE_PATH set, using default voice")
            self._voice_state = self._model.get_state_for_audio_prompt("cosette")

        logger.info("Pocket TTS loaded successfully")

    async def generate(self, text: str) -> dict:
        """
        Generate WAV audio from text.

        Args:
            text: Text to synthesize

        Returns:
            dict with audio_id, audio_url, content_type
        """
        if not self._model:
            raise RuntimeError("Pocket TTS model not loaded — call load() first")

        audio_id = str(uuid.uuid4())
        output_path = os.path.join(AUDIO_DIR, f"{audio_id}.wav")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._generate_sync, text, output_path)

        logger.info(f"Generated TTS audio: {audio_id}")
        return {
            "audio_id": audio_id,
            "audio_url": f"/static/audio/{audio_id}.wav",
            "content_type": "audio/wav",
        }

    def _generate_sync(self, text: str, output_path: str):
        """Synchronous generation (runs in thread pool)."""
        audio = self._model.generate_audio(self._voice_state, text)
        scipy.io.wavfile.write(output_path, self._model.sample_rate, audio.numpy())

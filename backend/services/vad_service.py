"""
Silero VAD Service for speech detection and interruption detection.
Two modes: 'speech' for end-of-utterance, 'interrupt' for quick speech detection.
"""
import logging
import torch
from silero_vad import load_silero_vad, VADIterator

logger = logging.getLogger(__name__)


class VADService:
    """Wraps Silero VAD with two sensitivity modes."""

    def __init__(self):
        logger.info("Loading Silero VAD model...")
        self.model = load_silero_vad()

        # Speech mode: detect end-of-utterance (600ms silence)
        self.speech_iterator = VADIterator(
            self.model,
            threshold=0.5,
            sampling_rate=16000,
            min_silence_duration_ms=600,
            speech_pad_ms=30,
        )

        # Interrupt mode: detect any speech quickly (100ms silence, lower threshold)
        self.interrupt_iterator = VADIterator(
            self.model,
            threshold=0.3,
            sampling_rate=16000,
            min_silence_duration_ms=100,
            speech_pad_ms=0,
        )

        self.mode = "speech"
        logger.info("Silero VAD loaded successfully")

    def process_chunk(self, pcm_bytes: bytes) -> dict | None:
        """
        Process 512 samples of int16 PCM audio.

        Args:
            pcm_bytes: 1024 bytes of int16 PCM at 16kHz

        Returns:
            {'start': ...} when speech begins,
            {'end': ...} when speech ends,
            or None if no event.
        """
        audio = torch.frombuffer(bytearray(pcm_bytes), dtype=torch.int16).float() / 32768.0
        iterator = self.interrupt_iterator if self.mode == "interrupt" else self.speech_iterator
        return iterator(audio)

    def set_mode(self, mode: str):
        """Switch between 'speech' and 'interrupt' detection modes."""
        self.mode = mode
        # Reset the relevant iterator when switching
        if mode == "speech":
            self.speech_iterator.reset_states()
        else:
            self.interrupt_iterator.reset_states()
        logger.debug(f"VAD mode switched to: {mode}")

    def reset(self):
        """Reset both iterators."""
        self.speech_iterator.reset_states()
        self.interrupt_iterator.reset_states()

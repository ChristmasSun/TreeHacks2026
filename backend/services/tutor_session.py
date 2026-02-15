"""
Per-session state machine for the audio pipeline.
Coordinates VAD, speculative LLM, Pocket TTS, and Deepgram forwarding.
"""
import asyncio
import json
import logging
from enum import Enum
from typing import Optional

from fastapi import WebSocket

from services.llm_service import build_system_prompt, fetch_rtms_transcripts, active_meeting_id
from services.speculative_llm import SpeculativeLLM
from services.vad_service import VADService
from services.pocket_tts_service import PocketTTSService

logger = logging.getLogger(__name__)


class SessionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    AVATAR_SPEAKING = "avatar_speaking"


class TutorSession:
    """
    Manages one student's audio session.

    Audio frames flow: frontend → handle_audio_frame() → Silero VAD + Deepgram
    Transcripts flow: Deepgram → handle_deepgram_transcript() → speculative LLM
    On speech end: cached LLM response → Pocket TTS → vad_speech_end message
    """

    def __init__(
        self,
        websocket: WebSocket,
        tts_service: PocketTTSService,
        student_name: str = "Student",
        meeting_id: Optional[str] = None,
    ):
        self.ws = websocket
        self.student_name = student_name
        self.meeting_id = meeting_id
        self.state = SessionState.IDLE
        self.conversation_history: list[dict] = []

        # Services
        self.vad = VADService()
        self.speculative = SpeculativeLLM()
        self.tts = tts_service  # Shared across sessions (model pre-loaded)

        # Deepgram WebSocket (set externally after connection)
        self.deepgram_ws = None

        # Accumulated transcript from Deepgram finals
        self._accumulated_transcript = ""
        # Latest interim for display
        self._latest_interim = ""

    async def handle_audio_frame(self, pcm_bytes: bytes):
        """
        Process a 512-sample int16 PCM frame.
        Forwards to Deepgram and runs Silero VAD.
        """
        # Forward to Deepgram for transcription
        if self.deepgram_ws:
            try:
                await self.deepgram_ws.send(pcm_bytes)
            except Exception as e:
                logger.warning(f"Deepgram send error: {e}")

        # Run VAD
        vad_event = self.vad.process_chunk(pcm_bytes)

        if vad_event:
            import sys
            print(f"[VAD] Event: {vad_event} (state={self.state.value}, mode={self.vad.mode})", file=sys.stderr, flush=True)
            if "start" in vad_event:
                await self._on_speech_start()
            elif "end" in vad_event:
                await self._on_speech_end()

    async def handle_deepgram_transcript(self, transcript: str, is_final: bool):
        """
        Called when Deepgram sends a transcript result.
        Feeds speculative LLM and updates frontend display.
        """
        if not transcript:
            return

        if is_final:
            # Accumulate finals for the complete utterance
            if self._accumulated_transcript:
                self._accumulated_transcript += " " + transcript
            else:
                self._accumulated_transcript = transcript

        # Use the most complete text available
        current_text = self._accumulated_transcript or transcript
        if not is_final:
            # For interims, append to accumulated
            current_text = (self._accumulated_transcript + " " + transcript).strip() if self._accumulated_transcript else transcript

        self._latest_interim = current_text

        if self.state == SessionState.LISTENING:
            # Feed speculative LLM on every transcript update
            system_prompt = await self._build_prompt(was_interrupted=False)
            await self.speculative.on_interim_transcript(
                current_text, system_prompt, self.conversation_history
            )

            # Send interim to frontend for display
            try:
                await self.ws.send_json({"type": "interim_transcript", "text": current_text})
            except Exception:
                pass

    async def _on_speech_start(self):
        """VAD detected speech start."""
        import sys
        print(f"[Session] speech_start (state={self.state.value})", file=sys.stderr, flush=True)
        if self.state == SessionState.IDLE:
            self.state = SessionState.LISTENING
            self._accumulated_transcript = ""
            self._latest_interim = ""

            try:
                await self.ws.send_json({"type": "vad_speech_start"})
            except Exception:
                pass

        elif self.state == SessionState.AVATAR_SPEAKING:
            # Interruption detected
            logger.info("Interruption detected during avatar speech")
            try:
                await self.ws.send_json({"type": "interrupt_detected"})
            except Exception:
                pass

            # Reset and start listening for the interrupting speech
            await self.speculative.reset()
            self.vad.set_mode("speech")
            self.state = SessionState.LISTENING
            self._accumulated_transcript = ""
            self._latest_interim = ""

    async def _on_speech_end(self):
        """VAD detected speech end."""
        import sys
        print(f"[Session] speech_end (state={self.state.value}, accumulated='{self._accumulated_transcript[:50]}', interim='{self._latest_interim[:50]}')", file=sys.stderr, flush=True)
        if self.state != SessionState.LISTENING:
            print(f"[Session] IGNORING speech_end — not in LISTENING state", file=sys.stderr, flush=True)
            return

        self.state = SessionState.PROCESSING

        # Wait briefly for Deepgram to finalize
        await asyncio.sleep(0.15)

        final_text = self._accumulated_transcript.strip() or self._latest_interim.strip()
        if not final_text:
            self.state = SessionState.IDLE
            logger.debug("Speech ended but no transcript → IDLE")
            return

        logger.info(f"Speech ended, final transcript: {final_text[:80]}...")

        # Get LLM response (from speculative cache or fresh call)
        system_prompt = await self._build_prompt(was_interrupted=False)
        response = await self.speculative.get_response(
            final_text, system_prompt, self.conversation_history
        )

        # Generate TTS audio
        try:
            audio_result = await self.tts.generate(response)
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            # Fall back to text-only response
            await self.ws.send_json({
                "type": "vad_speech_end",
                "transcript": final_text,
                "response": response,
                "audio_url": None,
            })
            self.state = SessionState.IDLE
            return

        # Update conversation history
        self.conversation_history.append({"role": "student", "text": final_text})
        self.conversation_history.append({"role": "avatar", "text": response})

        # Send complete response to frontend
        await self.ws.send_json({
            "type": "vad_speech_end",
            "transcript": final_text,
            "response": response,
            "audio_url": audio_result["audio_url"],
        })

        self.state = SessionState.AVATAR_SPEAKING
        self.vad.set_mode("interrupt")
        logger.debug("Response sent → AVATAR_SPEAKING")

    def on_avatar_done(self):
        """Called when frontend signals avatar finished speaking."""
        self.state = SessionState.IDLE
        self.vad.set_mode("speech")
        self.vad.reset()
        self._accumulated_transcript = ""
        self._latest_interim = ""
        logger.debug("Avatar done → IDLE")

    def on_avatar_speaking(self):
        """Called when frontend signals avatar started speaking."""
        self.state = SessionState.AVATAR_SPEAKING
        self.vad.set_mode("interrupt")

    async def _build_prompt(self, was_interrupted: bool) -> str:
        """Build system prompt with meeting context."""
        transcript_context = ""
        try:
            transcript_context = await fetch_rtms_transcripts(
                self.meeting_id or active_meeting_id
            )
        except Exception:
            pass
        return build_system_prompt(self.student_name, transcript_context, was_interrupted)

    async def close(self):
        """Cleanup session resources."""
        await self.speculative.close()

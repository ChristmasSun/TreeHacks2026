"""
Per-session state machine for the audio pipeline.
Coordinates VAD, speculative LLM, and Deepgram forwarding.
"""
import asyncio
import logging
import sys
import time
from enum import Enum
from typing import Optional

from fastapi import WebSocket

from services.heygen_lite_client import HeyGenLiteClient
from services.llm_service import build_system_prompt, fetch_rtms_transcripts, active_meeting_id, get_lecture_transcript
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
    On speech end: LLM response → vad_speech_end message → HeyGen speaks
    """

    def __init__(
        self,
        websocket: WebSocket,
        tts_service: PocketTTSService,
        heygen_lite: HeyGenLiteClient,
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
        self.tts = tts_service
        self.heygen_lite = heygen_lite

        # Wire HeyGen LITE callbacks
        self.heygen_lite._on_speak_ended = self._on_heygen_speak_ended

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
        # Forward to Deepgram — but NOT while avatar is speaking or processing
        if self.deepgram_ws and self.state not in (SessionState.AVATAR_SPEAKING, SessionState.PROCESSING):
            try:
                await self.deepgram_ws.send(pcm_bytes)
            except Exception as e:
                logger.warning(f"Deepgram send error: {e}")

        # Run VAD
        vad_event = self.vad.process_chunk(pcm_bytes)

        if vad_event:
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
            if self._accumulated_transcript:
                self._accumulated_transcript += " " + transcript
            else:
                self._accumulated_transcript = transcript

        current_text = self._accumulated_transcript or transcript
        if not is_final:
            current_text = (self._accumulated_transcript + " " + transcript).strip() if self._accumulated_transcript else transcript

        self._latest_interim = current_text

        if self.state == SessionState.LISTENING:
            system_prompt = await self._build_prompt()
            await self.speculative.on_interim_transcript(
                current_text, system_prompt, self.conversation_history
            )

            try:
                await self.ws.send_json({"type": "interim_transcript", "text": current_text})
            except Exception:
                pass

    async def _on_speech_start(self):
        """VAD detected speech start."""
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
            # User interrupted — stop avatar immediately and listen
            print(f"[Session] INTERRUPT — stopping avatar, switching to listen", file=sys.stderr, flush=True)
            try:
                await self.heygen_lite.interrupt()
            except Exception as e:
                print(f"[Session] HeyGen interrupt error: {e}", file=sys.stderr, flush=True)
            try:
                await self.ws.send_json({"type": "interrupt_detected"})
            except Exception:
                pass

            await self.speculative.reset()
            self.vad.set_mode("speech")
            self.state = SessionState.LISTENING
            self._accumulated_transcript = ""
            self._latest_interim = ""

    async def _on_speech_end(self):
        """VAD detected speech end."""
        print(f"[Session] speech_end (state={self.state.value}, accumulated='{self._accumulated_transcript[:50]}', interim='{self._latest_interim[:50]}')", file=sys.stderr, flush=True)

        if self.state != SessionState.LISTENING:
            return

        self.state = SessionState.PROCESSING

        # Wait for Deepgram to finalize
        await asyncio.sleep(0.4)

        final_text = self._accumulated_transcript.strip() or self._latest_interim.strip()
        if not final_text:
            self.state = SessionState.IDLE
            return

        # Get LLM response
        system_prompt = await self._build_prompt()
        print(f"[Session] Getting LLM response for: {final_text[:60]}", file=sys.stderr, flush=True)
        response = await self.speculative.get_response(
            final_text, system_prompt, self.conversation_history
        )
        print(f"[Session] LLM response: {response[:80]}", file=sys.stderr, flush=True)

        # Update conversation history
        self.conversation_history.append({"role": "student", "text": final_text})
        self.conversation_history.append({"role": "avatar", "text": response})

        # Send text to frontend for chat display
        await self.ws.send_json({
            "type": "vad_speech_end",
            "transcript": final_text,
            "response": response,
        })

        # Generate TTS audio and send to HeyGen LITE for lip-sync
        self.state = SessionState.AVATAR_SPEAKING
        self.vad.set_mode("interrupt")

        try:
            pcm_audio = await self.tts.generate_pcm(response)
            await self.heygen_lite.send_audio(pcm_audio)
        except Exception as e:
            print(f"[Session] TTS/HeyGen LITE error: {e}", file=sys.stderr, flush=True)
            # Fall back to idle if audio pipeline fails
            self.state = SessionState.IDLE
            self.vad.set_mode("speech")
            return

        print(f"[Session] Audio sent to HeyGen → AVATAR_SPEAKING", file=sys.stderr, flush=True)

    async def _on_heygen_speak_ended(self):
        """Called by HeyGen LITE when avatar finishes speaking."""
        print("[Session] HeyGen speak_ended → IDLE", file=sys.stderr, flush=True)
        self.state = SessionState.IDLE
        self.vad.set_mode("speech")
        self.vad.reset()
        self._accumulated_transcript = ""
        self._latest_interim = ""
        try:
            await self.ws.send_json({"type": "avatar_done"})
        except Exception:
            pass

    def on_avatar_done(self):
        """Called when frontend signals avatar finished speaking (legacy fallback)."""
        self.state = SessionState.IDLE
        self.vad.set_mode("speech")
        self.vad.reset()
        self._accumulated_transcript = ""
        self._latest_interim = ""

    def on_avatar_speaking(self):
        """Called when frontend signals avatar started speaking (legacy fallback)."""
        self.state = SessionState.AVATAR_SPEAKING
        self.vad.set_mode("interrupt")

    async def _build_prompt(self) -> str:
        """Build system prompt with lecture transcript + live RTMS context."""
        transcript_context = ""
        # Include pre-loaded lecture transcript as primary context
        lecture_text = get_lecture_transcript()
        if lecture_text:
            transcript_context = lecture_text[-3000:]
        # Append live RTMS transcript as supplementary context
        try:
            live_context = await fetch_rtms_transcripts(
                self.meeting_id or active_meeting_id
            )
            if live_context:
                transcript_context += f"\n\nLIVE CLASS DISCUSSION:\n{live_context[-1500:]}"
        except Exception:
            pass
        return build_system_prompt(self.student_name, transcript_context, False)

    async def close(self):
        """Cleanup session resources."""
        await self.speculative.close()
        if self.heygen_lite:
            await self.heygen_lite.close()

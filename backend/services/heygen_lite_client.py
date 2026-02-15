"""
LiveAvatar LITE (Custom) mode WebSocket client.
Sends PocketTTS audio to LiveAvatar for avatar lip-sync over WebSocket.
Video is delivered separately via LiveKit WebRTC.
"""
import asyncio
import base64
import json
import logging
import os
import sys
import uuid
from typing import Optional, Callable, Awaitable

import numpy as np
import websockets

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000
BYTES_PER_SAMPLE = 2  # int16
CHUNK_DURATION_S = 1.0
CHUNK_BYTES = int(SAMPLE_RATE * CHUNK_DURATION_S) * BYTES_PER_SAMPLE  # 48000 bytes
KEEP_ALIVE_INTERVAL_S = 120  # Send keep-alive every 2 minutes (5 min idle timeout)


class HeyGenLiteClient:
    """Manages a LiveAvatar LITE WebSocket session for custom audio lip-sync."""

    def __init__(self):
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._connected = asyncio.Event()
        self._on_speak_started: Optional[Callable[[], Awaitable[None]]] = None
        self._on_speak_ended: Optional[Callable[[], Awaitable[None]]] = None
        self._session_token: str = ""

    async def connect(self, ws_url: str, session_token: str = ""):
        """Connect to LiveAvatar LITE WebSocket and wait for 'connected' state."""
        self._session_token = session_token
        print(f"[LiveAvatar LITE] Connecting to {ws_url[:80]}...", file=sys.stderr, flush=True)
        self._ws = await websockets.connect(ws_url)
        self._reader_task = asyncio.create_task(self._read_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        await asyncio.wait_for(self._connected.wait(), timeout=30.0)
        print("[LiveAvatar LITE] Connected and ready", file=sys.stderr, flush=True)

    async def _read_loop(self):
        """Read and dispatch events from LiveAvatar WebSocket."""
        try:
            async for msg in self._ws:
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("type", "")
                print(f"[LiveAvatar LITE] Event: {event_type} → {json.dumps(data)[:200]}", file=sys.stderr, flush=True)

                if event_type == "session.state_updated":
                    state = data.get("state", "")
                    print(f"[LiveAvatar LITE] Session state: {state}", file=sys.stderr, flush=True)
                    if state == "connected":
                        self._connected.set()

                elif event_type == "agent.speak_started":
                    print("[LiveAvatar LITE] Avatar started speaking", file=sys.stderr, flush=True)
                    if self._on_speak_started:
                        await self._on_speak_started()

                elif event_type == "agent.speak_ended":
                    print("[LiveAvatar LITE] Avatar finished speaking", file=sys.stderr, flush=True)
                    if self._on_speak_ended:
                        await self._on_speak_ended()

        except websockets.ConnectionClosed:
            print("[LiveAvatar LITE] WebSocket closed", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[LiveAvatar LITE] Read loop error: {e}", file=sys.stderr, flush=True)

    async def _keepalive_loop(self):
        """Send periodic keep-alive to prevent 5-minute idle timeout."""
        try:
            while True:
                await asyncio.sleep(KEEP_ALIVE_INTERVAL_S)
                if self._ws:
                    await self._ws.send(json.dumps({
                        "type": "session.keep_alive",
                        "event_id": str(uuid.uuid4()),
                    }))
                    print("[LiveAvatar LITE] Sent keep-alive", file=sys.stderr, flush=True)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[LiveAvatar LITE] Keep-alive error: {e}", file=sys.stderr, flush=True)

    async def send_audio(self, pcm_int16: np.ndarray):
        """
        Send int16 PCM 24kHz audio to LiveAvatar for lip-sync.
        Audio is chunked into ~1s segments and base64 encoded.
        """
        if not self._ws:
            raise RuntimeError("Not connected to LiveAvatar LITE WebSocket")

        raw_bytes = pcm_int16.tobytes()
        num_chunks = (len(raw_bytes) + CHUNK_BYTES - 1) // CHUNK_BYTES
        event_id = str(uuid.uuid4())
        print(f"[LiveAvatar LITE] Sending {num_chunks} audio chunks ({len(raw_bytes)} bytes total) event_id={event_id[:8]}", file=sys.stderr, flush=True)

        offset = 0
        while offset < len(raw_bytes):
            chunk = raw_bytes[offset:offset + CHUNK_BYTES]
            b64_chunk = base64.b64encode(chunk).decode("ascii")

            await self._ws.send(json.dumps({
                "type": "agent.speak",
                "event_id": event_id,
                "audio": b64_chunk,
            }))
            offset += CHUNK_BYTES

        await self._ws.send(json.dumps({
            "type": "agent.speak_end",
            "event_id": event_id,
        }))
        print("[LiveAvatar LITE] All chunks sent + speak_end", file=sys.stderr, flush=True)

    async def interrupt(self):
        """Interrupt current avatar speech."""
        if self._ws:
            print("[LiveAvatar LITE] Sending interrupt", file=sys.stderr, flush=True)
            await self._ws.send(json.dumps({"type": "agent.interrupt"}))

    async def start_listening(self):
        """Transition avatar to listening pose."""
        if self._ws:
            await self._ws.send(json.dumps({
                "type": "agent.start_listening",
                "event_id": str(uuid.uuid4()),
            }))

    async def stop_listening(self):
        """Transition avatar to idle pose."""
        if self._ws:
            await self._ws.send(json.dumps({
                "type": "agent.stop_listening",
                "event_id": str(uuid.uuid4()),
            }))

    async def close(self):
        """Cleanup WebSocket, tasks, and stop session."""
        if self._keepalive_task:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()

        # Stop the session via REST API
        if self._session_token:
            try:
                import httpx
                base_url = os.environ.get("LIVEAVATAR_BASE_URL", "https://api.heygen.com")
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"{base_url}/v1/sessions/stop",
                        headers={
                            "Authorization": f"Bearer {self._session_token}",
                            "Content-Type": "application/json",
                        },
                    )
                    print("[LiveAvatar LITE] Session stopped via API", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[LiveAvatar LITE] Session stop error: {e}", file=sys.stderr, flush=True)

        print("[LiveAvatar LITE] Closed", file=sys.stderr, flush=True)

"""
Speculative LLM execution for low-latency responses.
Starts generating on interim transcripts, cancels and restarts on new input.
Caches completed responses for instant retrieval when utterance ends.
"""
import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"


def _is_junk_response(text: str) -> bool:
    """Filter out useless responses like '...', single punctuation, etc."""
    stripped = text.strip()
    if len(stripped) < 5:
        return True
    # All punctuation / ellipsis
    if re.fullmatch(r'[\.\!\?\-\–\—\…\s]+', stripped):
        return True
    return False


@dataclass
class SpeculativeCache:
    transcript: str = ""
    response: str = ""
    ready: bool = False


class SpeculativeLLM:
    """Manages speculative LLM execution with cancel-and-restart on each interim transcript."""

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=10.0)
        self._current_task: Optional[asyncio.Task] = None
        self._cache = SpeculativeCache()
        self._lock = asyncio.Lock()
        self._api_key = os.getenv("CEREBRAS_API_KEY", "")

    async def on_interim_transcript(
        self, transcript: str, system_prompt: str, history: list
    ):
        """
        Called on every interim transcript. Cancels previous in-flight request
        and starts a new Cerebras API call.
        """
        async with self._lock:
            # Cancel previous task if still running
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()

            self._current_task = asyncio.create_task(
                self._generate(transcript, system_prompt, history)
            )

    async def _generate(
        self, transcript: str, system_prompt: str, history: list
    ):
        """Make Cerebras API call and store result in cache."""
        try:
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history (last 6 messages)
            for msg in history[-6:]:
                messages.append(
                    {
                        "role": "user" if msg.get("role") == "student" else "assistant",
                        "content": msg.get("text", ""),
                    }
                )

            messages.append({"role": "user", "content": transcript})

            response = await self._client.post(
                CEREBRAS_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()

            text = ""
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                text = msg.get("content") or msg.get("text", "")

            # Filter junk responses
            if not text or _is_junk_response(text):
                print(f"[SpecLLM] Junk/empty response for '{transcript[:40]}': '{text}'", file=sys.stderr, flush=True)
                return

            print(f"[SpecLLM] Cached response for '{transcript[:40]}': {text[:60]}", file=sys.stderr, flush=True)

            async with self._lock:
                self._cache = SpeculativeCache(
                    transcript=transcript, response=text, ready=True
                )

        except asyncio.CancelledError:
            # Expected when a new interim transcript arrives
            pass
        except Exception as e:
            print(f"[SpecLLM] Error: {type(e).__name__}: {e}", file=sys.stderr, flush=True)

    async def get_response(self, final_transcript: str, system_prompt: str, history: list) -> str:
        """
        Called when VAD detects speech end. Returns cached response if available,
        otherwise waits for current task or makes a fresh call.
        """
        async with self._lock:
            # Check if cache matches final transcript
            if self._cache.ready and self._cache.transcript.strip() == final_transcript.strip():
                response = self._cache.response
                self._cache = SpeculativeCache()
                print(f"[SpecLLM] Cache HIT (exact match)", file=sys.stderr, flush=True)
                return response

            task = self._current_task

        # Wait for in-flight task to complete
        if task and not task.done():
            try:
                await task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            # After waiting, check if cache matches OR is close enough
            if self._cache.ready:
                cached_t = self._cache.transcript.strip()
                final_t = final_transcript.strip()
                # Accept cache if transcript is a substring match (Deepgram may add/trim words)
                if cached_t == final_t or cached_t in final_t or final_t in cached_t:
                    response = self._cache.response
                    self._cache = SpeculativeCache()
                    print(f"[SpecLLM] Cache HIT (fuzzy match: '{cached_t[:30]}' ~ '{final_t[:30]}')", file=sys.stderr, flush=True)
                    return response
                else:
                    # Cache is stale — clear it
                    print(f"[SpecLLM] Cache STALE: cached='{cached_t[:30]}' vs final='{final_t[:30]}'", file=sys.stderr, flush=True)
                    self._cache = SpeculativeCache()

        # Cache miss — make a fresh blocking call
        print(f"[SpecLLM] Cache MISS — fresh call for: {final_transcript[:50]}", file=sys.stderr, flush=True)
        return await self._generate_blocking(final_transcript, system_prompt, history)

    async def _generate_blocking(
        self, transcript: str, system_prompt: str, history: list
    ) -> str:
        """Blocking LLM call as fallback when cache misses."""
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-6:]:
            messages.append(
                {
                    "role": "user" if msg.get("role") == "student" else "assistant",
                    "content": msg.get("text", ""),
                }
            )
        messages.append({"role": "user", "content": transcript})

        try:
            response = await self._client.post(
                CEREBRAS_API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                text = msg.get("content") or msg.get("text", "")
                if text and not _is_junk_response(text):
                    print(f"[SpecLLM] Blocking call OK: {text[:60]}", file=sys.stderr, flush=True)
                    return text
            print(f"[SpecLLM] Blocking call returned junk, raw: {str(data)[:200]}", file=sys.stderr, flush=True)
            return "I'm sorry, I'm having trouble responding right now. Could you repeat that?"
        except Exception as e:
            print(f"[SpecLLM] Blocking call FAILED: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            return "I'm sorry, I'm having trouble responding right now. Could you repeat that?"

    async def reset(self):
        """Cancel any in-flight task and clear cache."""
        async with self._lock:
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
            self._cache = SpeculativeCache()

    async def close(self):
        """Cleanup HTTP client."""
        await self._client.aclose()

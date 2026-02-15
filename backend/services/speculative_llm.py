"""
Speculative LLM execution for low-latency responses.
Starts generating on interim transcripts, cancels and restarts on new input.
Caches completed responses for instant retrieval when utterance ends.
"""
import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"


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
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            import sys
            print(f"[SpecLLM] Cerebras response keys: {list(data.keys())}", file=sys.stderr, flush=True)
            if "choices" in data and data["choices"]:
                msg = data["choices"][0].get("message", {})
                text = msg.get("content") or msg.get("text", "")
                print(f"[SpecLLM] Response: {text[:80]}...", file=sys.stderr, flush=True)
            else:
                print(f"[SpecLLM] Unexpected response: {str(data)[:200]}", file=sys.stderr, flush=True)
                text = ""
            if not text:
                return

            async with self._lock:
                self._cache = SpeculativeCache(
                    transcript=transcript, response=text, ready=True
                )
                logger.debug(f"Speculative cache updated for: {transcript[:50]}...")

        except asyncio.CancelledError:
            # Expected when a new interim transcript arrives
            pass
        except Exception as e:
            logger.error(f"Speculative LLM error: {e}")

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
                logger.info("Speculative cache HIT")
                return response

            task = self._current_task

        # Wait for in-flight task to complete
        if task and not task.done():
            try:
                await task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            if self._cache.ready:
                response = self._cache.response
                self._cache = SpeculativeCache()
                logger.info("Speculative cache HIT (after wait)")
                return response

        # Cache miss — make a fresh blocking call
        logger.info("Speculative cache MISS — making fresh call")
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
                    "max_tokens": 100,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Blocking LLM call failed: {e}")
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

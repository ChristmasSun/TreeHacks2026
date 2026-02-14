import os
import asyncio
from dedalus_labs import AsyncDedalus

MODEL = "openai/gpt-5.2"

_client: AsyncDedalus | None = None


def get_client() -> AsyncDedalus:
    global _client
    if _client is None:
        api_key = os.environ.get("DEDALUS_API_KEY")
        if not api_key:
            raise ValueError(
                "DEDALUS_API_KEY environment variable is required. "
                "Set it in your .env file or export it."
            )
        _client = AsyncDedalus(api_key=api_key)
    return _client


async def call_llm(prompt: str, temperature: float = 0.3) -> str:
    """Call GPT 5.2 via Dedalus Labs API with retry logic."""
    client = get_client()
    max_retries = 5
    base_delay = 2

    for attempt in range(1, max_retries + 1):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = str(e)
            rate_limited = (
                "429" in error_msg
                or "rate" in error_msg.lower()
                or "quota" in error_msg.lower()
            )
            if not rate_limited or attempt == max_retries:
                raise
            delay = base_delay * attempt
            print(f"[LLM] Rate limited, retrying in {delay}s (attempt {attempt}/{max_retries})")
            await asyncio.sleep(delay)

    raise RuntimeError("Exhausted retries for LLM call")

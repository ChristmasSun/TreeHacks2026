import os
import asyncio
import httpx
import tempfile
from typing import TypedDict

TRANSCRIPTION_URL = "https://api.dedaluslabs.ai/v1/audio/transcriptions"
TRANSCRIPTION_MODEL = "groq/whisper-large-v3"
CHUNK_DURATION_SECS = 600  # 10 minutes per chunk

_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
}


def _audio_mime_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return _MIME_TYPES.get(ext, "application/octet-stream")


class WordTimestamp(TypedDict):
    word: str
    start: float
    end: float


class SegmentTimestamp(TypedDict):
    start: float
    end: float
    text: str
    words: list[WordTimestamp]


async def get_audio_duration(audio_path: str) -> float:
    """Get duration in seconds using ffprobe."""
    process = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return float(stdout.decode().strip())


async def split_audio(audio_path: str, chunk_dir: str) -> list[str]:
    """Split audio into chunks using ffmpeg in parallel. Returns list of chunk paths."""
    duration = await get_audio_duration(audio_path)

    async def _split_one(i: int, start: int) -> str | None:
        chunk_path = os.path.join(chunk_dir, f"chunk_{i:03d}.mp3")
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(start),
            "-t", str(CHUNK_DURATION_SECS),
            "-acodec", "libmp3lame",
            "-ab", "64k",       # compress to stay well under 25MB
            "-ac", "1",         # mono
            "-ar", "16000",     # 16kHz is plenty for speech
            chunk_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
            return chunk_path
        return None

    results = await asyncio.gather(*[
        _split_one(i, start)
        for i, start in enumerate(range(0, int(duration) + 1, CHUNK_DURATION_SECS))
    ])
    return [p for p in results if p is not None]


async def transcribe_chunk(client: httpx.AsyncClient, api_key: str, chunk_path: str) -> str:
    """Transcribe a single audio chunk."""
    with open(chunk_path, "rb") as f:
        response = await client.post(
            TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (os.path.basename(chunk_path), f, _audio_mime_type(chunk_path))},
            data={
                "model": TRANSCRIPTION_MODEL,
                "language": "en",
                "response_format": "verbose_json",
            },
            timeout=300.0,
        )

    if response.status_code != 200:
        raise RuntimeError(f"Transcription failed (HTTP {response.status_code}): {response.text[:300]}")

    return response.json().get("text", "").strip()


async def transcribe(audio_path: str) -> str:
    """Transcribe an audio file, splitting into chunks if needed."""
    api_key = os.environ.get("DEDALUS_API_KEY")
    if not api_key:
        raise ValueError("DEDALUS_API_KEY environment variable is required.")

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"[Transcribe] Input: {audio_path} ({file_size_mb:.1f} MB)")

    if file_size_mb <= 20:
        # Small enough to send directly
        print("[Transcribe] Transcribing in one request...")
        async with httpx.AsyncClient() as client:
            text = await transcribe_chunk(client, api_key, audio_path)
        print(f"[Transcribe] Done ({len(text.split())} words)")
        return text

    # Split into chunks
    chunk_dir = tempfile.mkdtemp(prefix="transcribe_chunks_")
    try:
        print(f"[Transcribe] File too large, splitting into {CHUNK_DURATION_SECS}s chunks...")
        chunks = await split_audio(audio_path, chunk_dir)
        print(f"[Transcribe] Split into {len(chunks)} chunks")

        transcribe_sem = asyncio.Semaphore(3)

        async def _transcribe_with_limit(client: httpx.AsyncClient, i: int, path: str) -> str:
            chunk_size = os.path.getsize(path) / (1024 * 1024)
            async with transcribe_sem:
                print(f"[Transcribe] Chunk {i+1}/{len(chunks)} ({chunk_size:.1f} MB)...")
                return await transcribe_chunk(client, api_key, path)

        async with httpx.AsyncClient() as client:
            texts = await asyncio.gather(*[
                _transcribe_with_limit(client, i, path)
                for i, path in enumerate(chunks)
            ])

        full_text = " ".join(texts)
        print(f"[Transcribe] Done ({len(full_text.split())} words total)")
        return full_text
    finally:
        # Clean up chunks
        for f in os.listdir(chunk_dir):
            os.unlink(os.path.join(chunk_dir, f))
        os.rmdir(chunk_dir)


async def timestamp_audio(
    audio_path: str,
    client: httpx.AsyncClient | None = None,
) -> list[SegmentTimestamp]:
    """Run Whisper on an audio file and return segments with word-level timestamps.

    This is designed for short clips (e.g. TTS voiceovers) that don't need chunking.
    Pass a shared ``client`` for connection pooling across calls.
    """
    api_key = os.environ.get("DEDALUS_API_KEY")
    if not api_key:
        raise ValueError("DEDALUS_API_KEY environment variable is required.")

    async def _do_request(c: httpx.AsyncClient) -> httpx.Response:
        with open(audio_path, "rb") as f:
            return await c.post(
                TRANSCRIPTION_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (os.path.basename(audio_path), f, _audio_mime_type(audio_path))},
                data={
                    "model": TRANSCRIPTION_MODEL,
                    "language": "en",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                },
                timeout=120.0,
            )

    if client is not None:
        response = await _do_request(client)
    else:
        async with httpx.AsyncClient() as c:
            response = await _do_request(c)

    if response.status_code != 200:
        raise RuntimeError(f"Timestamp transcription failed (HTTP {response.status_code}): {response.text[:300]}")

    data = response.json()
    segments: list[SegmentTimestamp] = []

    # Extract from segments (which contain word-level detail)
    for seg in data.get("segments", []):
        words: list[WordTimestamp] = []
        for w in seg.get("words", []):
            words.append({
                "word": w.get("word", "").strip(),
                "start": round(w.get("start", 0.0), 2),
                "end": round(w.get("end", 0.0), 2),
            })
        segments.append({
            "start": round(seg.get("start", 0.0), 2),
            "end": round(seg.get("end", 0.0), 2),
            "text": seg.get("text", "").strip(),
            "words": words,
        })

    # Fallback: if segments exist but have no words, build from top-level words
    if segments and all(not s["words"] for s in segments):
        top_words = data.get("words", [])
        if top_words:
            all_words = [
                {
                    "word": w.get("word", "").strip(),
                    "start": round(w.get("start", 0.0), 2),
                    "end": round(w.get("end", 0.0), 2),
                }
                for w in top_words
            ]
            # Attach words to their matching segments by time overlap
            for seg in segments:
                seg["words"] = [
                    w for w in all_words
                    if w["start"] >= seg["start"] - 0.05 and w["end"] <= seg["end"] + 0.05
                ]

    return segments

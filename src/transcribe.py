import os
import asyncio
import httpx
import tempfile

TRANSCRIPTION_URL = "https://api.dedaluslabs.ai/v1/audio/transcriptions"
TRANSCRIPTION_MODEL = "groq/whisper-large-v3"
CHUNK_DURATION_SECS = 600  # 10 minutes per chunk


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
    """Split audio into chunks using ffmpeg. Returns list of chunk paths."""
    duration = await get_audio_duration(audio_path)
    chunks = []

    for i, start in enumerate(range(0, int(duration) + 1, CHUNK_DURATION_SECS)):
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
            chunks.append(chunk_path)

    return chunks


async def transcribe_chunk(client: httpx.AsyncClient, api_key: str, chunk_path: str) -> str:
    """Transcribe a single audio chunk."""
    with open(chunk_path, "rb") as f:
        response = await client.post(
            TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (os.path.basename(chunk_path), f, "audio/mpeg")},
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

        texts = []
        async with httpx.AsyncClient() as client:
            for i, chunk_path in enumerate(chunks):
                chunk_size = os.path.getsize(chunk_path) / (1024 * 1024)
                print(f"[Transcribe] Chunk {i+1}/{len(chunks)} ({chunk_size:.1f} MB)...")
                text = await transcribe_chunk(client, api_key, chunk_path)
                texts.append(text)

        full_text = " ".join(texts)
        print(f"[Transcribe] Done ({len(full_text.split())} words total)")
        return full_text
    finally:
        # Clean up chunks
        for f in os.listdir(chunk_dir):
            os.unlink(os.path.join(chunk_dir, f))
        os.rmdir(chunk_dir)

import os
import asyncio


async def download_audio(url: str, output_dir: str) -> str:
    """Download audio from a YouTube video URL using yt-dlp."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "audio.mp3")

    print(f"[Download] Downloading audio from {url}...")

    cmd = [
        "yt-dlp",
        "-x",                        # extract audio only
        "--audio-format", "mp3",
        "--audio-quality", "0",       # best quality
        "-o", output_path,
        "--no-playlist",
        url,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {stderr.decode()[:500]}")

    if not os.path.exists(output_path):
        raise RuntimeError(f"yt-dlp did not produce {output_path}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[Download] Saved audio ({size_mb:.1f} MB) to {output_path}")
    return output_path

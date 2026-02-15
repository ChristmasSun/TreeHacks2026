import os
import asyncio


async def download_audio(url: str, output_dir: str) -> str:
    """Download audio from a YouTube video URL using yt-dlp.

    Args:
        url: YouTube video URL.
        output_dir: Directory to save the audio file.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "audio.%(ext)s")

    print(f"[Download] Downloading audio from {url}...")

    cmd = [
        "yt-dlp",
        "-x",                        # extract audio only
        "-o", output_path,
        "--no-playlist",
        url,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=None,   # let yt-dlp print progress to terminal
        stderr=None,
    )
    try:
        await asyncio.wait_for(process.wait(), timeout=600)
    except asyncio.TimeoutError:
        process.kill()
        raise RuntimeError("yt-dlp timed out after 120 seconds")

    if process.returncode != 0:
        raise RuntimeError(f"yt-dlp failed with exit code {process.returncode}")

    # yt-dlp picks the extension; find whatever audio file it wrote
    audio_file = next(
        (f for f in os.listdir(output_dir) if f.startswith("audio.")),
        None,
    )
    if audio_file is None:
        raise RuntimeError(f"yt-dlp did not produce an audio file in {output_dir}")

    final_path = os.path.join(output_dir, audio_file)
    size_mb = os.path.getsize(final_path) / (1024 * 1024)
    print(f"[Download] Saved audio ({size_mb:.1f} MB) to {final_path}")
    return final_path

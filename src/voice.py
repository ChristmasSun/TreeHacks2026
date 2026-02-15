import asyncio
import os
import subprocess

import scipy.io.wavfile
import torch
import torchaudio

from pocket_tts import TTSModel


# ── Voice sample extraction ──────────────────────────────────────────────────


def extract_voice_sample(
    audio_path: str,
    output_dir: str,
    start_secs: float = 120,
    duration_secs: float = 30,
) -> str:
    """Extract a clip from the lecture audio for voice cloning."""
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "voice_sample.wav")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(start_secs),
            "-t", str(duration_secs),
            "-ar", "24000", "-ac", "1",
            output_path,
        ],
        capture_output=True,
        check=True,
    )
    print(f"[Voice] Extracted {duration_secs}s clip from {start_secs}s: {output_path}")
    return output_path


# ── TTS generation ───────────────────────────────────────────────────────────

_tts_model: TTSModel | None = None


def _get_tts_model() -> TTSModel:
    global _tts_model
    if _tts_model is None:
        print("[Voice] Loading Pocket TTS model...")
        _tts_model = TTSModel.load_model()
    return _tts_model


def generate_voiceover(text: str, voice_sample_path: str, output_path: str) -> str:
    """Generate a voiceover WAV from text using a voice sample.

    Returns:
        Path to the generated WAV file.
    """
    model = _get_tts_model()
    voice_state = model.get_state_for_audio_prompt(voice_sample_path)
    audio = model.generate_audio(voice_state, text)
    scipy.io.wavfile.write(output_path, model.sample_rate, audio.numpy())
    print(f"[Voice] Generated voiceover: {output_path}")
    return output_path


def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


async def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> str:
    """Merge a voiceover WAV onto a video, stretching video to match audio duration."""
    audio_duration = get_audio_duration(audio_path)

    # Get video duration
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
    )
    video_duration = float(result.stdout.strip())

    if video_duration < 0.1:
        raise RuntimeError("Video has zero duration")

    # Calculate speed factor to match video to audio duration
    speed = video_duration / audio_duration

    # Clamp speed to reasonable range (0.5x to 2x)
    speed = max(0.5, min(2.0, speed))

    if abs(speed - 1.0) < 0.05:
        # Close enough — just merge directly with shortest
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]
    else:
        # Retime video to match audio duration
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter:v", f"setpts={1/speed}*PTS",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg merge failed: {stderr.decode()[:500]}")

    return output_path

import os
import re
import json
import asyncio
from pathlib import Path

from .llm import call_llm
from .render import sanitize_code, render_manim_code
from .transcribe import transcribe
from .download import download_audio
from .voice import extract_voice_sample, generate_voiceover, get_audio_duration, merge_audio_video

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

WORDS_PER_SCENE = 600
LLM_SEMAPHORE = asyncio.Semaphore(5)


def read_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def estimate_scene_count(transcript: str) -> int:
    """Estimate scene count based on transcript length (~1 scene per 600 words, clamped 3-12)."""
    word_count = len(transcript.split())
    count = max(3, min(12, round(word_count / WORDS_PER_SCENE)))
    return count


async def split_transcript_into_scenes(transcript: str) -> list[str]:
    """Split a lecture transcript into focused scene descriptions, scaled to length."""
    scene_count = estimate_scene_count(transcript)
    template = read_prompt("split_scenes.txt")
    prompt = template.format(transcript=transcript, scene_count=scene_count)

    word_count = len(transcript.split())
    print(f"[Pipeline] Splitting transcript ({word_count} words) into ~{scene_count} scenes...")
    response = await call_llm(prompt, temperature=0.3)

    json_match = re.search(r"\[.*\]", response, re.DOTALL)
    if json_match:
        try:
            scenes = json.loads(json_match.group(0))
            if isinstance(scenes, list) and all(isinstance(s, str) for s in scenes):
                print(f"[Pipeline] Split into {len(scenes)} scenes")
                return scenes
        except json.JSONDecodeError:
            pass

    # Fallback: split by sentences
    print("[Pipeline] Failed to parse scenes JSON, falling back to sentence splitting")
    return [s.strip() for s in transcript.split(".") if len(s.strip()) > 10] or [transcript]


def _chunk_transcript_for_scenes(transcript: str, scene_count: int) -> list[str]:
    """Split transcript into roughly equal chunks, one per scene."""
    words = transcript.split()
    chunk_size = max(1, len(words) // scene_count)
    chunks = []
    for i in range(scene_count):
        start = i * chunk_size
        end = start + chunk_size if i < scene_count - 1 else len(words)
        chunks.append(" ".join(words[start:end]))
    return chunks


async def generate_narration(scene_description: str, transcript_chunk: str) -> str:
    """Generate a TTS narration script for a scene."""
    template = read_prompt("generate_narration.txt")
    prompt = template.format(
        scene_description=scene_description,
        transcript_chunk=transcript_chunk,
    )

    async with LLM_SEMAPHORE:
        response = await call_llm(prompt, temperature=0.4)
    return response.strip()


def _build_narration_context(narration: str, duration: float) -> str:
    """Build the narration context string for the code generation prompt."""
    return (
        f"A voiceover will play over this animation. It lasts {duration:.1f} seconds.\n"
        f"Pace your animation to fill this time — the total of all run_time values and "
        f"self.wait() calls should sum to approximately {duration:.1f} seconds.\n"
        f"Time key visual reveals to match what the narration describes.\n"
        f"Narration text: \"{narration}\""
    )


async def generate_manim_code(
    description: str,
    narration_context: str = "No voiceover — use natural pacing with self.wait() between steps.",
) -> str:
    """Generate initial Manim code for a scene description."""
    template = read_prompt("generate_code.txt")
    cheat_sheet = read_prompt("manim_cheat_sheet.txt")
    prompt = template.format(
        description=description,
        cheat_sheet=cheat_sheet,
        narration_context=narration_context,
    )

    async with LLM_SEMAPHORE:
        response = await call_llm(prompt, temperature=0.3)
    return sanitize_code(response)


async def correct_manim_code(
    code: str,
    error: str,
    description: str = "",
    narration_context: str = "No voiceover — use natural pacing.",
) -> str:
    """Correct failed Manim code based on an error message."""
    template = read_prompt("correct_code.txt")
    cheat_sheet = read_prompt("manim_cheat_sheet.txt")
    prompt = template.format(
        code=code,
        error=error,
        description=description,
        narration_context=narration_context,
        cheat_sheet=cheat_sheet,
    )

    async with LLM_SEMAPHORE:
        response = await call_llm(prompt, temperature=0.3)
    return sanitize_code(response)


async def process_single_clip(
    i: int,
    scene_description: str,
    transcript_chunk: str,
    output_dir: str,
    voice_sample_path: str | None = None,
) -> dict:
    """Process a single clip: narration first, then animation timed to match.

    Flow:
        1. Generate narration text from scene description + transcript
        2. Generate TTS audio, measure its duration
        3. Generate manim code with narration timing context
        4. Render manim video (with retry/correction loop)
        5. Merge audio onto video (stretching video if needed)
    """
    output_filename = f"clip_{i}.mp4"
    print(f"[Clip {i+1}] Starting: {scene_description[:60]}...")

    # ── Step 1: Generate narration ──────────────────────────────────────────
    narration_context = "No voiceover — use natural pacing with self.wait() between steps."
    voiceover_path = None
    narration_duration = 0.0

    if voice_sample_path:
        try:
            print(f"[Clip {i+1}] Generating narration...")
            narration = await generate_narration(scene_description, transcript_chunk)
            print(f"[Clip {i+1}] Narration: {narration[:80]}...")

            # ── Step 2: Generate TTS audio ──────────────────────────────────
            voiceover_path = os.path.join(output_dir, f"voiceover_{i}.wav")
            await asyncio.to_thread(
                generate_voiceover, narration, voice_sample_path, voiceover_path,
            )
            narration_duration = get_audio_duration(voiceover_path)
            print(f"[Clip {i+1}] Voiceover duration: {narration_duration:.1f}s")

            # ── Step 3: Build timing context for code gen ───────────────────
            narration_context = _build_narration_context(narration, narration_duration)

        except Exception as e:
            print(f"[Clip {i+1}] Narration/TTS failed, proceeding without voiceover: {e}")
            voiceover_path = None

    # ── Step 4: Generate and render manim code ──────────────────────────────
    code = None
    error = None
    video_path = None

    for attempt in range(1, 4):
        print(f"[Clip {i+1}] Render attempt {attempt}/3")
        try:
            if code is None:
                code = await generate_manim_code(scene_description, narration_context)
            else:
                code = await correct_manim_code(
                    code, error,
                    description=scene_description,
                    narration_context=narration_context,
                )

            video_path, error = await render_manim_code(code, output_dir, output_filename)

            if error is None:
                print(f"[Clip {i+1}] Rendered successfully: {video_path}")
                break

            print(f"[Clip {i+1}] Render failed on attempt {attempt}")
        except Exception as e:
            print(f"[Clip {i+1}] Error on attempt {attempt}: {e}")
            error = str(e)

    if video_path is None or error is not None:
        print(f"[Clip {i+1}] FAILED after 3 attempts, skipping")
        return {"success": False, "index": i}

    # ── Step 5: Merge voiceover onto video ──────────────────────────────────
    if voiceover_path and os.path.exists(voiceover_path):
        try:
            merged_path = os.path.join(output_dir, f"clip_{i}_voiced.mp4")
            await merge_audio_video(video_path, voiceover_path, merged_path)
            print(f"[Clip {i+1}] Merged voiceover successfully")
            video_path = merged_path
        except Exception as e:
            print(f"[Clip {i+1}] Voiceover merge failed (keeping silent video): {e}")

    return {"success": True, "index": i, "path": video_path}


async def process_all_clips(
    scenes: list[str],
    transcript_chunks: list[str],
    output_dir: str,
    voice_sample_path: str | None = None,
) -> list[dict]:
    """Process all clips in parallel."""
    tasks = [
        process_single_clip(i, scene, transcript_chunks[i], output_dir, voice_sample_path)
        for i, scene in enumerate(scenes)
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for i, result in enumerate(raw_results):
        if isinstance(result, Exception):
            print(f"[Clip {i+1}] Exception: {result}")
            results.append({"success": False, "index": i})
        else:
            results.append(result)

    return results


async def stitch_clips(results: list[dict], output_dir: str) -> str | None:
    """Concatenate successful clips into a single final video using ffmpeg."""
    successful = [r for r in results if r["success"]]
    if not successful:
        return None

    successful.sort(key=lambda r: r["index"])

    if len(successful) == 1:
        return successful[0]["path"]

    # Write ffmpeg concat file
    concat_path = os.path.join(output_dir, "concat.txt")
    with open(concat_path, "w") as f:
        for r in successful:
            abs_path = os.path.abspath(r["path"])
            escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    final_path = os.path.join(output_dir, "final.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_path,
        "-c", "copy",
        final_path,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        print(f"[Stitch] ffmpeg failed: {stderr.decode()}")
        return None

    os.unlink(concat_path)
    print(f"[Stitch] Final video: {final_path}")
    return final_path


async def run(url: str, output_dir: str) -> str | None:
    """Main pipeline: YouTube URL -> download -> transcription -> Manim video."""
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Download audio from YouTube
    audio_path = await download_audio(url, output_dir)

    # Step 2: Transcribe audio
    print("[Pipeline] Transcribing audio...")
    transcript = await transcribe(audio_path)

    # Save transcript for reference
    transcript_save_path = os.path.join(output_dir, "transcript.txt")
    Path(transcript_save_path).write_text(transcript, encoding="utf-8")
    print(f"[Pipeline] Transcript saved to {transcript_save_path}")

    # Step 3: Extract voice sample for TTS cloning
    print("[Pipeline] Extracting voice sample from lecture audio...")
    voice_dir = os.path.join(output_dir, "voice")
    try:
        voice_sample_path = await asyncio.to_thread(
            extract_voice_sample, audio_path, voice_dir,
        )
    except Exception as e:
        print(f"[Pipeline] Voice extraction failed, proceeding without voiceover: {e}")
        voice_sample_path = None

    # Step 4: Split into scenes
    scenes = await split_transcript_into_scenes(transcript)
    transcript_chunks = _chunk_transcript_for_scenes(transcript, len(scenes))

    # Step 5: Generate narration, TTS, then animation (timed to narration) for all clips
    print(f"\n[Pipeline] Generating {len(scenes)} clips in parallel...")
    results = await process_all_clips(scenes, transcript_chunks, output_dir, voice_sample_path)

    successful = sum(1 for r in results if r["success"])
    print(f"\n[Pipeline] {successful}/{len(scenes)} clips rendered successfully")

    if successful == 0:
        print("Error: all clips failed to render")
        return None

    # Step 6: Stitch into final video
    print("\n[Pipeline] Stitching final video...")
    return await stitch_clips(results, output_dir)

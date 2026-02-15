import os
import re
import json
import asyncio
import shutil
from pathlib import Path
from typing import TypedDict

from .llm import call_llm
from .render import sanitize_code, render_manim_code
from .transcribe import transcribe
from .download import download_audio
from .voice import extract_voice_sample, generate_voiceover, get_audio_duration, merge_audio_video

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

LLM_SEMAPHORE = asyncio.Semaphore(5)


class ScenePlan(TypedDict):
    concept: str
    description: str
    transcript_excerpt: str


def read_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


async def split_transcript_into_scenes(transcript: str) -> list[ScenePlan]:
    """Split transcript into ordered core-concept scenes with aligned excerpts."""
    template = read_prompt("split_scenes.txt")
    prompt = template.format(transcript=transcript)

    word_count = len(transcript.split())
    print(f"[Pipeline] Extracting concept-based scenes from transcript ({word_count} words)...")
    response = await call_llm(prompt, temperature=0.3)

    json_match = re.search(r"\[.*\]", response, re.DOTALL)
    if not json_match:
        raise ValueError("Scene splitting failed: LLM response did not contain a JSON array.")

    try:
        parsed = json.loads(json_match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Scene splitting failed: invalid JSON from LLM ({exc})") from exc

    if not isinstance(parsed, list) or not parsed:
        raise ValueError("Scene splitting failed: expected a non-empty JSON array.")

    scenes: list[ScenePlan] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"Scene splitting failed: scene {idx + 1} is not an object.")

        concept = item.get("concept")
        description = item.get("description")
        transcript_excerpt = item.get("transcript_excerpt")

        if not isinstance(concept, str) or not concept.strip():
            raise ValueError(f"Scene splitting failed: scene {idx + 1} missing non-empty 'concept'.")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Scene splitting failed: scene {idx + 1} missing non-empty 'description'.")
        if not isinstance(transcript_excerpt, str) or not transcript_excerpt.strip():
            raise ValueError(
                f"Scene splitting failed: scene {idx + 1} missing non-empty 'transcript_excerpt'."
            )

        scenes.append(
            {
                "concept": concept.strip(),
                "description": description.strip(),
                "transcript_excerpt": transcript_excerpt.strip(),
            }
        )

    print(f"[Pipeline] Planned {len(scenes)} concept-based scenes")
    return scenes


async def generate_narration(scene_description: str, transcript_excerpt: str) -> str:
    """Generate a TTS narration script for a scene."""
    template = read_prompt("generate_narration.txt")
    prompt = template.format(
        scene_description=scene_description,
        transcript_chunk=transcript_excerpt,
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
    scene: ScenePlan,
    videos_dir: str,
    code_dir: str,
    voice_sample_path: str | None = None,
    max_attempts: int = 3,
) -> dict:
    """Process a single clip: narration first, then animation timed to match.

    Flow:
        1. Generate narration text from scene description + transcript
        2. Generate TTS audio, measure its duration
        3. Generate manim code with narration timing context
        4. Render manim video (with retry/correction loop)
        5. Merge audio onto video (stretching video if needed)
    """
    concept = scene["concept"]
    scene_description = scene["description"]
    transcript_excerpt = scene["transcript_excerpt"]
    scene_tag = f"scene_{i:03d}"
    output_filename = f"{scene_tag}.mp4"
    print(f"[Clip {i+1}] Starting [{concept}]: {scene_description[:60]}...")

    # ── Step 1: Generate narration ──────────────────────────────────────────
    narration_context = "No voiceover — use natural pacing with self.wait() between steps."
    voiceover_path = None
    narration = ""
    narration_duration = 0.0

    if voice_sample_path:
        try:
            print(f"[Clip {i+1}] Generating narration...")
            narration = await generate_narration(scene_description, transcript_excerpt)
            print(f"[Clip {i+1}] Narration: {narration[:80]}...")

            # ── Step 2: Generate TTS audio ──────────────────────────────────
            voiceover_path = os.path.join(videos_dir, f"{scene_tag}_voiceover.wav")
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

    for attempt in range(1, max_attempts + 1):
        print(f"[Clip {i+1}] Render attempt {attempt}/{max_attempts}")
        attempt_label = f"{scene_tag}_attempt_{attempt}"
        code_path = os.path.join(code_dir, f"{attempt_label}.py")
        error_path = os.path.join(code_dir, f"{attempt_label}_error.txt")
        try:
            if code is None:
                code = await generate_manim_code(scene_description, narration_context)
            else:
                code = await correct_manim_code(
                    code, error,
                    description=scene_description,
                    narration_context=narration_context,
                )

            Path(code_path).write_text(code, encoding="utf-8")
            video_path, error = await render_manim_code(code, videos_dir, output_filename)

            if error is None:
                print(f"[Clip {i+1}] Rendered successfully: {video_path}")
                break

            print(f"[Clip {i+1}] Render failed on attempt {attempt}")
            Path(error_path).write_text(error, encoding="utf-8")
        except Exception as e:
            print(f"[Clip {i+1}] Error on attempt {attempt}: {e}")
            error = str(e)
            Path(error_path).write_text(error, encoding="utf-8")

    if video_path is None or error is not None:
        print(f"[Clip {i+1}] FAILED after {max_attempts} attempts, skipping")
        return {
            "success": False,
            "index": i,
            "concept": concept,
            "description": scene_description,
            "narration": narration,
            "narration_duration": narration_duration,
            "error": error,
        }

    # Keep explicit silent artifact for inspection.
    silent_path = os.path.join(videos_dir, f"{scene_tag}_silent.mp4")
    shutil.copy2(video_path, silent_path)
    final_path = silent_path

    # ── Step 5: Merge voiceover onto video ──────────────────────────────────
    if voiceover_path and os.path.exists(voiceover_path):
        try:
            merged_path = os.path.join(videos_dir, f"{scene_tag}_voiced.mp4")
            await merge_audio_video(silent_path, voiceover_path, merged_path)
            print(f"[Clip {i+1}] Merged voiceover successfully")
            final_path = merged_path
        except Exception as e:
            print(f"[Clip {i+1}] Voiceover merge failed (keeping silent video): {e}")

    return {
        "success": True,
        "index": i,
        "concept": concept,
        "description": scene_description,
        "narration": narration,
        "narration_duration": narration_duration,
        "path": final_path,
        "silent_path": silent_path,
        "voiceover_path": voiceover_path,
    }


async def process_all_clips(
    scenes: list[ScenePlan],
    videos_dir: str,
    code_dir: str,
    voice_sample_path: str | None = None,
    max_attempts: int = 3,
    concurrency: int = 4,
) -> list[dict]:
    """Process all clips in parallel."""
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def run_with_limit(i: int, scene: ScenePlan) -> dict:
        async with semaphore:
            return await process_single_clip(
                i,
                scene,
                videos_dir,
                code_dir,
                voice_sample_path,
                max_attempts=max_attempts,
            )

    tasks = [
        run_with_limit(i, scene)
        for i, scene in enumerate(scenes)
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results = []
    for i, result in enumerate(raw_results):
        if isinstance(result, Exception):
            print(f"[Clip {i+1}] Exception: {result}")
            results.append(
                {
                    "success": False,
                    "index": i,
                    "concept": scenes[i]["concept"],
                    "description": scenes[i]["description"],
                    "narration": "",
                    "narration_duration": 0.0,
                    "error": str(result),
                }
            )
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


async def run(
    url: str,
    output_dir: str,
    clip_concurrency: int | None = None,
    max_render_attempts: int | None = None,
) -> str | None:
    """Main pipeline: YouTube URL -> download -> transcription -> Manim video."""
    os.makedirs(output_dir, exist_ok=True)
    videos_dir = os.path.join(output_dir, "videos")
    code_dir = os.path.join(output_dir, "animation-code")
    os.makedirs(videos_dir, exist_ok=True)
    os.makedirs(code_dir, exist_ok=True)

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
    scene_plan_path = os.path.join(output_dir, "scene_plan.json")
    Path(scene_plan_path).write_text(json.dumps(scenes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Pipeline] Scene plan saved to {scene_plan_path}")

    # Step 5: Generate narration, TTS, then animation (timed to narration) for all clips
    if clip_concurrency is None:
        clip_concurrency = int(os.getenv("PIPELINE_CLIP_CONCURRENCY", "4"))
    if max_render_attempts is None:
        max_render_attempts = int(os.getenv("PIPELINE_MAX_RENDER_ATTEMPTS", "3"))
    print(
        f"\n[Pipeline] Generating {len(scenes)} clips in parallel "
        f"(concurrency={clip_concurrency}, max_attempts={max_render_attempts})..."
    )
    results = await process_all_clips(
        scenes,
        videos_dir,
        code_dir,
        voice_sample_path,
        max_attempts=max_render_attempts,
        concurrency=clip_concurrency,
    )
    results_path = os.path.join(output_dir, "render_results.json")
    Path(results_path).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Pipeline] Render results saved to {results_path}")

    narration_scripts = [
        {
            "index": r.get("index"),
            "concept": r.get("concept"),
            "scene_description": r.get("description"),
            "narration": r.get("narration"),
            "narration_duration": r.get("narration_duration"),
            "success": r.get("success"),
        }
        for r in sorted(results, key=lambda x: x.get("index", 0))
    ]
    narration_path = os.path.join(output_dir, "narration_scripts.json")
    Path(narration_path).write_text(
        json.dumps(narration_scripts, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[Pipeline] Narration scripts saved to {narration_path}")

    successful = sum(1 for r in results if r["success"])
    print(f"\n[Pipeline] {successful}/{len(scenes)} clips rendered successfully")

    if successful == 0:
        print("Error: all clips failed to render")
        return None

    # Step 6: Stitch into final video
    print("\n[Pipeline] Stitching final video...")
    return await stitch_clips(results, videos_dir)

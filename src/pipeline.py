import os
import re
import json
import asyncio
from pathlib import Path

from .llm import call_llm
from .render import sanitize_code, render_manim_code

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

WORDS_PER_SCENE = 600


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


async def generate_manim_code(description: str) -> str:
    """Generate initial Manim code for a scene description."""
    template = read_prompt("generate_code.txt")
    cheat_sheet = read_prompt("manim_cheat_sheet.txt")
    prompt = template.format(description=description, cheat_sheet=cheat_sheet)

    response = await call_llm(prompt, temperature=0.3)
    return sanitize_code(response)


async def correct_manim_code(code: str, error: str) -> str:
    """Correct failed Manim code based on an error message."""
    template = read_prompt("correct_code.txt")
    cheat_sheet = read_prompt("manim_cheat_sheet.txt")
    prompt = template.format(code=code, error=error, cheat_sheet=cheat_sheet)

    response = await call_llm(prompt, temperature=0.3)
    return sanitize_code(response)


async def process_single_clip(i: int, scene_description: str, output_dir: str) -> dict:
    """Process a single clip with up to 3 generation/correction attempts."""
    output_filename = f"clip_{i}.mp4"
    print(f"[Clip {i+1}] Generating: {scene_description[:60]}...")

    code = None
    error = None

    for attempt in range(1, 4):
        print(f"[Clip {i+1}] Attempt {attempt}/3")
        try:
            if code is None:
                code = await generate_manim_code(scene_description)
            else:
                code = await correct_manim_code(code, error)

            video_path, error = await render_manim_code(code, output_dir, output_filename)

            if error is None:
                print(f"[Clip {i+1}] Rendered successfully: {video_path}")
                return {"success": True, "index": i, "path": video_path}

            print(f"[Clip {i+1}] Render failed on attempt {attempt}")
        except Exception as e:
            print(f"[Clip {i+1}] Error on attempt {attempt}: {e}")
            error = str(e)

    print(f"[Clip {i+1}] FAILED after 3 attempts, skipping")
    return {"success": False, "index": i}


async def process_clips_in_batches(scenes: list[str], output_dir: str, batch_size: int = 3) -> list[dict]:
    """Process clips in parallel batches."""
    all_results = []
    total = len(scenes)

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_num = (batch_start // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"\n=== Batch {batch_num}/{total_batches} (Clips {batch_start+1}-{batch_end}) ===")

        tasks = [
            process_single_clip(batch_start + j, scene, output_dir)
            for j, scene in enumerate(scenes[batch_start:batch_end])
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                print(f"[Clip {batch_start+j+1}] Exception: {result}")
                all_results.append({"success": False, "index": batch_start + j})
            else:
                all_results.append(result)

    return all_results


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
            # Escape single quotes in path for ffmpeg
            escaped = r["path"].replace("'", "'\\''")
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


async def run(transcript_path: str, output_dir: str) -> str | None:
    """Main pipeline: transcript file -> Manim video."""
    os.makedirs(output_dir, exist_ok=True)

    transcript = Path(transcript_path).read_text(encoding="utf-8")
    if not transcript.strip():
        print("Error: transcript file is empty")
        return None

    print(f"[Pipeline] Read transcript ({len(transcript)} chars)")

    # Step 1: Split into scenes
    scenes = await split_transcript_into_scenes(transcript)

    # Step 2: Generate and render clips
    print(f"\n[Pipeline] Generating {len(scenes)} clips...")
    results = await process_clips_in_batches(scenes, output_dir)

    successful = sum(1 for r in results if r["success"])
    print(f"\n[Pipeline] {successful}/{len(scenes)} clips rendered successfully")

    if successful == 0:
        print("Error: all clips failed to render")
        return None

    # Step 3: Stitch into final video
    print("\n[Pipeline] Stitching final video...")
    return await stitch_clips(results, output_dir)

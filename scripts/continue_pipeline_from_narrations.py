import argparse
import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import (
    _build_narration_context,
    correct_manim_code,
    generate_manim_code,
    stitch_clips,
)
from src.render import render_manim_code
from src.voice import (
    extract_voice_sample,
    generate_voiceover,
    get_audio_duration,
    merge_audio_video,
)


def load_env_like_cli(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Continue the pipeline from narration JSON: generate Manim code, "
            "retry-correct renders, merge voice audio, and optionally stitch."
        )
    )
    parser.add_argument(
        "--input",
        default="test-output/narration_scripts_v2.json",
        help="Path to narration JSON generated from scene plan.",
    )
    parser.add_argument(
        "--output-root",
        default="test-output",
        help="Root output directory where animation-code/ and videos/ will be written.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start index in the narration list.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=4,
        help="How many scenes to process from --start (default: 4). Use <=0 for all remaining.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Render attempts per scene (default: 3).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="How many scenes to process in parallel (default: 4).",
    )
    parser.add_argument(
        "--voice-sample",
        default="",
        help="Optional voice sample WAV path. If omitted, script tries output-root/voice/voice_sample.wav.",
    )
    parser.add_argument(
        "--skip-voice",
        action="store_true",
        help="Skip TTS and audio merge (render silent clips only).",
    )
    parser.add_argument(
        "--no-stitch",
        action="store_true",
        help="Do not stitch successful clips into a final video.",
    )
    return parser.parse_args()


def load_narration_entries(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Input narration JSON not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Narration JSON must be a list.")
    entries: list[dict] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {i} is not an object.")
        description = item.get("scene_description")
        narration = item.get("narration")
        concept = item.get("concept", f"scene_{i}")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Entry {i} missing non-empty scene_description.")
        if not isinstance(narration, str) or not narration.strip():
            raise ValueError(f"Entry {i} missing non-empty narration.")
        entries.append(
            {
                "index": int(item.get("index", i)),
                "concept": str(concept).strip(),
                "scene_description": description.strip(),
                "narration": narration.strip(),
            }
        )
    return entries


def select_entries(entries: list[dict], start: int, limit: int) -> list[dict]:
    if start < 0:
        raise ValueError("--start must be >= 0")
    if start >= len(entries):
        return []
    if limit <= 0:
        return entries[start:]
    return entries[start : start + limit]


def resolve_voice_sample(args: argparse.Namespace, output_root: Path) -> Path | None:
    if args.skip_voice:
        return None

    if args.voice_sample:
        path = Path(args.voice_sample)
        if not path.exists():
            raise FileNotFoundError(f"Provided --voice-sample does not exist: {path}")
        return path

    default_path = output_root / "voice" / "voice_sample.wav"
    if default_path.exists():
        return default_path

    audio_path = output_root / "audio.mp3"
    if not audio_path.exists():
        raise FileNotFoundError(
            "No voice sample found and no audio.mp3 available to extract from. "
            "Provide --voice-sample or add test-output/audio.mp3."
        )
    voice_dir = output_root / "voice"
    print(f"[Setup] Extracting voice sample from {audio_path}...")
    voice_path = extract_voice_sample(str(audio_path), str(voice_dir))
    return Path(voice_path)


async def process_entry(
    entry: dict,
    videos_dir: Path,
    code_dir: Path,
    max_attempts: int,
    voice_sample_path: Path | None,
) -> dict:
    index = entry["index"]
    concept = entry["concept"]
    description = entry["scene_description"]
    narration = entry["narration"]

    scene_tag = f"scene_{index:03d}"
    print(f"[Scene {index}] {concept}")

    narration_context = "No voiceover — use natural pacing with self.wait() between steps."
    voiceover_path: Path | None = None

    if voice_sample_path is not None:
        try:
            voiceover_path = videos_dir / f"{scene_tag}_voiceover.wav"
            await asyncio.to_thread(
                generate_voiceover,
                narration,
                str(voice_sample_path),
                str(voiceover_path),
            )
            duration = get_audio_duration(str(voiceover_path))
            narration_context = _build_narration_context(narration, duration)
            print(f"[Scene {index}] Voiceover duration: {duration:.1f}s")
        except Exception as exc:
            print(f"[Scene {index}] Voice generation failed, proceeding silent: {exc}")
            voiceover_path = None

    code: str | None = None
    last_error: str | None = None
    rendered_path: str | None = None

    for attempt in range(1, max_attempts + 1):
        attempt_label = f"{scene_tag}_attempt_{attempt}"
        code_path = code_dir / f"{attempt_label}.py"
        error_path = code_dir / f"{attempt_label}_error.txt"

        try:
            if code is None:
                code = await generate_manim_code(description, narration_context)
            else:
                code = await correct_manim_code(
                    code=code,
                    error=last_error or "Unknown render failure",
                    description=description,
                    narration_context=narration_context,
                )

            code_path.write_text(code, encoding="utf-8")
            rendered_path, render_error = await render_manim_code(
                code=code,
                output_dir=str(videos_dir),
                file_name=f"{scene_tag}.mp4",
            )

            if render_error is None:
                break

            last_error = render_error
            error_path.write_text(render_error, encoding="utf-8")
            print(f"[Scene {index}] Attempt {attempt}/{max_attempts} failed.")
        except Exception as exc:
            last_error = str(exc)
            error_path.write_text(last_error, encoding="utf-8")
            print(f"[Scene {index}] Attempt {attempt}/{max_attempts} raised: {exc}")

    if rendered_path is None:
        return {
            "success": False,
            "index": index,
            "concept": concept,
            "error": last_error,
        }

    silent_target = videos_dir / f"{scene_tag}_silent.mp4"
    shutil.copy2(rendered_path, silent_target)
    final_target = silent_target

    if voiceover_path is not None and voiceover_path.exists():
        voiced_target = videos_dir / f"{scene_tag}_voiced.mp4"
        try:
            await merge_audio_video(
                video_path=str(silent_target),
                audio_path=str(voiceover_path),
                output_path=str(voiced_target),
            )
            final_target = voiced_target
        except Exception as exc:
            print(f"[Scene {index}] Voice merge failed, keeping silent video: {exc}")

    return {
        "success": True,
        "index": index,
        "concept": concept,
        "path": str(final_target),
        "silent_path": str(silent_target),
        "voiceover_path": str(voiceover_path) if voiceover_path else None,
    }


async def process_entry_with_limit(
    semaphore: asyncio.Semaphore,
    entry: dict,
    videos_dir: Path,
    code_dir: Path,
    max_attempts: int,
    voice_sample_path: Path | None,
) -> dict:
    async with semaphore:
        return await process_entry(
            entry=entry,
            videos_dir=videos_dir,
            code_dir=code_dir,
            max_attempts=max_attempts,
            voice_sample_path=voice_sample_path,
        )


async def run() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    load_env_like_cli(project_root)

    input_path = Path(args.input)
    output_root = Path(args.output_root)
    code_dir = output_root / "animation-code"
    videos_dir = output_root / "videos"
    code_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    entries = load_narration_entries(input_path)
    selected = select_entries(entries, args.start, args.limit)
    if not selected:
        print("No entries selected for processing.")
        return

    voice_sample_path = resolve_voice_sample(args, output_root)
    if voice_sample_path:
        print(f"[Setup] Using voice sample: {voice_sample_path}")

    concurrency = max(1, args.concurrency)
    print(f"[Setup] Processing {len(selected)} scene(s) with concurrency={concurrency}")

    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        process_entry_with_limit(
            semaphore=semaphore,
            entry=entry,
            videos_dir=videos_dir,
            code_dir=code_dir,
            max_attempts=args.max_attempts,
            voice_sample_path=voice_sample_path,
        )
        for entry in selected
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: list[dict] = []
    for entry, result in zip(selected, raw_results):
        if isinstance(result, Exception):
            print(f"[Scene {entry['index']}] Unexpected exception: {result}")
            results.append(
                {
                    "success": False,
                    "index": entry["index"],
                    "concept": entry["concept"],
                    "error": str(result),
                }
            )
        else:
            results.append(result)

    results_path = output_root / "render_results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Done] Saved scene results: {results_path}")

    if args.no_stitch:
        return

    stitch_input = [
        {"success": r["success"], "index": r["index"], "path": r["path"]}
        for r in results
        if r.get("success")
    ]
    if not stitch_input:
        print("[Done] No successful clips to stitch.")
        return

    final_path = await stitch_clips(stitch_input, str(videos_dir))
    if final_path:
        print(f"[Done] Stitched final video: {final_path}")
    else:
        print("[Done] Stitching failed.")


if __name__ == "__main__":
    asyncio.run(run())

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

# Load .env from project root
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

_CACHE_PATH = Path(__file__).parent.parent / ".cli_cache.json"


def _load_cache() -> dict | None:
    if _CACHE_PATH.exists():
        return json.loads(_CACHE_PATH.read_text())
    return None


def _save_cache(params: dict):
    _CACHE_PATH.write_text(json.dumps(params))


def _increment_output(output: str) -> str:
    """output/run-3 -> output/run-4, output/foo -> output/foo-2"""
    m = re.search(r"-(\d+)$", output)
    if m:
        n = int(m.group(1)) + 1
        return output[: m.start()] + f"-{n}"
    return output + "-2"


def _prompt(label: str, default: str) -> str:
    val = input(f"{label} [{default}]: ").strip()
    return val if val else default


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3Blue1Brown-style Manim videos from YouTube lectures"
    )
    parser.add_argument(
        "--again", "-a",
        action="store_true",
        help="Re-run with last cached parameters, incrementing the output folder number.",
    )
    args = parser.parse_args()

    if args.again:
        cached = _load_cache()
        if not cached:
            print("No cached run found. Run interactively first.", file=sys.stderr)
            sys.exit(1)
        cached["output"] = _increment_output(cached["output"])
        params = cached
        print(f"Re-running with cached params (output: {params['output']})")
    else:
        cached = _load_cache()
        default_url = cached["url"] if cached else ""
        default_output = cached["output"] if cached else "output"
        default_conc = str(cached["concurrency"]) if cached and cached["concurrency"] else "4"
        default_attempts = str(cached["max_attempts"]) if cached and cached["max_attempts"] else "3"

        url = _prompt("YouTube URL", default_url) if default_url else input("YouTube URL: ").strip()
        if not url:
            print("URL is required.", file=sys.stderr)
            sys.exit(1)
        output = _prompt("Output directory", default_output)
        concurrency = int(_prompt("Concurrency", default_conc))
        max_attempts = int(_prompt("Max attempts", default_attempts))

        params = {
            "url": url,
            "output": output,
            "concurrency": concurrency,
            "max_attempts": max_attempts,
        }

    _save_cache(params)

    # Import pipeline late to avoid heavy library imports (torch, torchaudio, etc.)
    # corrupting terminal state before interactive input() calls finish.
    from .pipeline import run

    result = asyncio.run(
        run(
            params["url"],
            params["output"],
            clip_concurrency=params["concurrency"],
            max_render_attempts=params["max_attempts"],
        )
    )

    if result:
        print(f"\nDone! Video saved to: {result}")
    else:
        print("\nFailed to generate video.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

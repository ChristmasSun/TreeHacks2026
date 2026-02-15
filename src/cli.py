import argparse
import asyncio
import os
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

from .pipeline import run


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3Blue1Brown-style Manim videos from YouTube lectures"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory for generated videos (default: output)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Number of scenes to process concurrently (default: 4 or PIPELINE_CLIP_CONCURRENCY).",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Maximum render/correction attempts per scene (default: 3 or PIPELINE_MAX_RENDER_ATTEMPTS).",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run(
            args.url,
            args.output,
            clip_concurrency=args.concurrency,
            max_render_attempts=args.max_attempts,
        )
    )

    if result:
        print(f"\nDone! Video saved to: {result}")
    else:
        print("\nFailed to generate video.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

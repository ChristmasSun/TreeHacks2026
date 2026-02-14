import argparse
import asyncio
import sys

from .pipeline import run


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3Blue1Brown-style Manim videos from lecture transcripts"
    )
    parser.add_argument("transcript", help="Path to lecture transcript text file")
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory for generated videos (default: output)",
    )
    args = parser.parse_args()

    result = asyncio.run(run(args.transcript, args.output))

    if result:
        print(f"\nDone! Video saved to: {result}")
    else:
        print("\nFailed to generate video.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
set -euo pipefail

ATTEMPTS_DIR="${1:-test-output/animation-code}"
MEDIA_DIR="${2:-/tmp/manim_attempt_compile}"

if [ ! -d "$ATTEMPTS_DIR" ]; then
  echo "error: attempts directory not found: $ATTEMPTS_DIR" >&2
  exit 1
fi

export PATH="/Library/TeX/texbin:$PATH"
mkdir -p "$MEDIA_DIR"

shopt -s nullglob
files=("$ATTEMPTS_DIR"/*.py)
if [ ${#files[@]} -eq 0 ]; then
  echo "error: no .py attempt files found in $ATTEMPTS_DIR" >&2
  exit 1
fi

for f in "${files[@]}"; do
  cls="$(
    sed -nE \
      's/^[[:space:]]*class[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)\(([^)]*Scene[^)]*)\):.*/\1/p' \
      "$f" | head -n 1
  )"
  [ -n "$cls" ] || cls="Scene"

  echo "===== $(basename "$f")  (class: $cls)"
  PYTHONUNBUFFERED=1 .venv/bin/python -m manim "$f" "$cls" \
    -o "$(basename "${f%.py}").mp4" \
    --media_dir "$MEDIA_DIR" \
    -v WARNING \
    -ql || true
done


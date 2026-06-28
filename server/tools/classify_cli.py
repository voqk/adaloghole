"""Stage-0 batch classifier — run saved frames through the vision classifier, no hardware.

Usage (from the server/ directory, with the venv active and a key set via /admin):

    python -m tools.classify_cli frames/*.jpg

Prints "path -> {label, confidence, reason}" per file. Handy for tuning the prompt and
program description against a folder of saved captures before any board arrives.
"""

import sys
from pathlib import Path

from app.classifier import classify_frame


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 1
    for p in paths:
        path = Path(p)
        try:
            verdict = classify_frame(path.read_bytes())
        except OSError as e:
            print(f"{p} -> read error: {e}")
            continue
        print(f"{p} -> {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

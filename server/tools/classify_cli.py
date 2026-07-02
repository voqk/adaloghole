"""Batch classifier — run saved frames through the vision classifier, no hardware.

Usage (from the server/ directory, with the venv active and a key set via /admin):

    python -m tools.classify_cli frames/*.jpg

Prints "path -> Verdict" per file. Handy for tuning the prompt and program
description against a folder of saved captures.
"""

import sys
from pathlib import Path

from app.contracts import Context
from app.roles.classifier.claude import ClaudeClassifier
from app.settings_store import get_settings


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 1
    classifier = ClaudeClassifier()
    context = Context(program=get_settings().program)
    for p in paths:
        path = Path(p)
        try:
            verdict = classifier.classify(path.read_bytes(), "image/jpeg", context)
        except OSError as e:
            print(f"{p} -> read error: {e}")
            continue
        print(f"{p} -> {verdict.model_dump()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

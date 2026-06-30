"""Device-facing API — what the ESP32 POSTs frames to.

    POST /classify   body = raw JPEG (Content-Type: image/jpeg)
      -> { label, confidence, reason, action: mute|unmute|none, muted }

The device reads `action` to decide whether to fire IR, and `muted` as the
authoritative state for its LCD.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from .classifier import classify_frame
from .decision import DecisionEngine
from .settings import get_settings

router = APIRouter()

# Debug artifacts for camera tuning (Stage D): the most recent frame + its verdict.
# Written best-effort to the gitignored data/ dir so they can be eyeballed while
# aiming the camera and tuning exposure. Overwritten each frame; never persisted.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _save_debug(body: bytes, result: dict) -> None:
    """Persist the last frame + verdict for tuning. Never raises into the request."""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        (_DATA_DIR / "last_frame.jpg").write_bytes(body)
        (_DATA_DIR / "last_verdict.json").write_text(json.dumps(result, indent=2))
        print(
            f"[classify] {len(body)}B -> label={result['label']} "
            f"conf={result['confidence']} action={result['action']} "
            f"muted={result['muted']} :: {result['reason']}",
            flush=True,
        )
    except Exception:
        pass  # tuning aid only — a disk/log hiccup must not break classification

# One shared engine for the single TV.
engine = DecisionEngine(flip_threshold=get_settings().flip_threshold)


def rebuild_engine(preserve_state: bool = True) -> None:
    """Rebuild the engine with the current flip_threshold (called after an admin edit)."""
    global engine
    new_engine = DecisionEngine(flip_threshold=get_settings().flip_threshold)
    if preserve_state:
        new_engine.muted = engine.muted  # keep current mute state across a threshold change
    engine = new_engine


@router.post("/classify")
async def classify(request: Request):
    body = await request.body()  # raw JPEG
    media_type = request.headers.get("content-type", "image/jpeg")
    if not media_type.startswith("image/"):
        media_type = "image/jpeg"
    # classify_frame is a blocking SDK call — run it off the event loop.
    verdict = await run_in_threadpool(classify_frame, body, media_type)
    decision = engine.feed(verdict["label"])
    result = {**verdict, **decision}  # {label, confidence, reason, action, muted}
    _save_debug(body, result)  # best-effort tuning aid; never breaks the response
    return result

"""Device-facing API — what the ESP32 POSTs frames to.

    POST /classify   body = raw JPEG (Content-Type: image/jpeg)
      -> { label, confidence, reason, action: mute|unmute|none, muted }

The device reads `action` to decide whether to fire IR, and `muted` as the
authoritative state for its LCD.
"""

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from .classifier import classify_frame
from .decision import DecisionEngine
from .settings import get_settings

router = APIRouter()

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
    return {**verdict, **decision}  # {label, confidence, reason, action, muted}

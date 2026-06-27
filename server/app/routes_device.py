"""Device-facing API — what the ESP32 POSTs frames to.  [STUB]

    POST /classify   body = raw JPEG (Content-Type: image/jpeg)
      -> { label, confidence, reason, action: mute|unmute|none, muted }

The device reads `action` to decide whether to fire IR, and `muted` as the
authoritative state for its LCD.
"""

# TODO: from fastapi import APIRouter, Request
# TODO: from .classifier import classify_frame
# TODO: from .decision import DecisionEngine  (one shared instance for the single TV)
# TODO: router = APIRouter()
# TODO: @router.post("/classify"): read body -> classify_frame -> engine.feed -> JSON

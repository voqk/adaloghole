"""The Brain's HTTP surface (architecture.md §8) — the wire binding of its seams.

    POST /frame         JPEG body (+X-Adaloghole-* meta headers) -> FrameResponse
    POST /classify      legacy alias of /frame with the flat response shape the
                        ESP32 firmware parses: {label, confidence, reason, action, muted}
    GET  /status        -> Status
    POST /control       Control -> Status
    GET  /settings      -> GenericSettings
    PUT  /settings      GenericSettings -> GenericSettings
    GET  /capabilities  -> Capabilities (proxied from the wired Actuator)
"""

import time

from fastapi import APIRouter, Request

from .contracts import Capabilities, Control, FrameMeta, FrameResponse, GenericSettings, Status

router = APIRouter()


def _meta_from_headers(request: Request) -> FrameMeta:
    h = request.headers

    def _num(name, cast):
        try:
            return cast(h[name])
        except (KeyError, ValueError):
            return None

    return FrameMeta(
        source_id=h.get("x-adaloghole-source-id", "unknown"),
        ts=_num("x-adaloghole-ts", float) or time.time(),
        seq=_num("x-adaloghole-seq", int) or 0,
        width=_num("x-adaloghole-width", int),
        height=_num("x-adaloghole-height", int),
    )


async def _handle_frame(request: Request) -> FrameResponse:
    body = await request.body()  # raw JPEG
    media_type = request.headers.get("content-type", "image/jpeg")
    if not media_type.startswith("image/"):
        media_type = "image/jpeg"
    return await request.app.state.brain.handle_frame(body, media_type, _meta_from_headers(request))


@router.post("/frame")
async def frame(request: Request) -> FrameResponse:
    return await _handle_frame(request)


@router.post("/classify")
async def classify(request: Request) -> dict:
    """Legacy device endpoint. The ESP32 reads exactly `action` and `muted`;
    always 200 (a failed classification is label=unknown, action=none)."""
    r = await _handle_frame(request)
    return {
        **r.verdict.model_dump(),
        "action": r.command.op if r.command else "none",
        "muted": r.status.av_state == "muted",
    }


@router.get("/status")
def status(request: Request) -> Status:
    return request.app.state.brain.status()


@router.post("/control")
def control(request: Request, body: Control) -> Status:
    return request.app.state.brain.control(body)


@router.get("/settings")
def get_settings(request: Request) -> GenericSettings:
    return request.app.state.brain.get_settings()


@router.put("/settings")
def put_settings(request: Request, body: GenericSettings) -> GenericSettings:
    return request.app.state.brain.put_settings(body)


@router.get("/capabilities")
def capabilities(request: Request) -> Capabilities:
    return request.app.state.brain.capabilities()

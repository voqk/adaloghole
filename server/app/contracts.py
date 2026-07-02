"""Data contracts between the five roles (architecture.md §4).

These shapes ARE the seams: the same fields travel as JSON on the wire when a
seam crosses devices, or as these objects for an in-process binding. Keep them
implementation-agnostic — nothing Claude-, OpenCV-, or LIRC-specific belongs
here.
"""

from typing import Literal

from pydantic import BaseModel

# Canonical verdict labels. The wire label for "the show itself" is "content";
# a classifier implementation may use different model-facing vocabulary
# internally but must map to these before returning a Verdict.
Label = Literal["content", "commercial", "unknown"]


class FrameMeta(BaseModel):
    """Frame metadata (Sensor -> Brain). The JPEG bytes travel out-of-band —
    as the HTTP body on the wire, or a bytes argument in-process."""

    source_id: str = "unknown"
    ts: float = 0.0
    seq: int = 0
    width: int | None = None
    height: int | None = None
    audio_level: float | None = None


class Context(BaseModel):
    """Optional hints to sharpen classification (Brain -> Classifier)."""

    program: str
    sport: str | None = None


class Verdict(BaseModel):
    """Classifier -> Brain."""

    label: Label
    confidence: float
    reason: str


class Command(BaseModel):
    """Brain -> Actuator."""

    op: Literal["mute", "unmute", "source_switch", "noop"]
    target: Literal["tv", "soundbar"] = "tv"
    code_ref: str = ""  # key into the Actuator's IR code catalog, e.g. "tv.mute"
    reason: str = ""
    ts: float = 0.0


class Ack(BaseModel):
    """Actuator -> Brain."""

    ok: bool
    executed: bool
    detail: str = ""


class Capabilities(BaseModel):
    """Actuator -> Brain."""

    can_mute: bool
    can_switch_source: bool = False
    targets: list[str] = []


class Control(BaseModel):
    """Controller -> Brain (the override knob)."""

    override: Literal["auto", "force_mute", "force_unmute"]
    lock: bool = False


class Status(BaseModel):
    """Brain -> Controller (what the LCD/UI renders)."""

    mode: Literal["auto", "override", "locked"]
    av_state: Literal["unmuted", "muted", "music"]
    last_label: Label | None = None
    last_confidence: float | None = None
    last_reason: str | None = None
    source_id: str | None = None
    uptime_s: float = 0.0


class GenericSettings(BaseModel):
    """Controller <-> Brain. GENERIC brain config only — classifier-private
    config (prompt/model/key) lives with the classifier implementation and
    never appears here."""

    sample_interval_s: float = 10.0
    flip_threshold: int = 2
    program: str = "a live sports broadcast such as a baseball game"
    soundbar_music_enabled: bool = False  # inert in Phase 1 (no "music" av_state yet)


class FrameResponse(BaseModel):
    """Response to a frame submission (POST /frame). `command` rides back so a
    combined Sensor+Actuator device can act on the reply without a second
    channel (architecture.md §5); it is set only when the state flipped."""

    verdict: Verdict
    status: Status
    command: Command | None = None

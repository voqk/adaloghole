# AdalogHole

An open-source device that watches your TV with a camera and mutes the
commercials using the **"analog hole"**. Baseball and other live sports are the
first target.

> Marketing site lives in the sibling `../adaloghole.com/` repo — its look and
> "wooden wedge" form factor are early inspiration and will likely change. This
> repo is the working system: software (server/classifier), firmware, and
> (eventually) CAD.
>
> **📐 Design lives in [`docs/architecture.md`](docs/architecture.md) — read it first.**

## The loop

1. **LOOK** — a camera grabs a still frame from the TV on a timer.
2. **DECIDE** — the frame is classified: content (the game) vs. commercial.
3. **ACT** — on a commercial, fire IR to mute the TV (or switch the soundbar);
   switch back when the game returns. A knob overrules it anytime.

## Architecture — five pluggable roles

The system is five roles, each defined by a **contract**, not an implementation:
**Sensor** (grabs frames) → **Classifier** (content vs. commercial) → **Brain**
(decision state machine + coordination) → **Actuator** (fires IR) →
**Controller** (knob + status + admin portal).

Each seam has two bindings from the *same* contract: an in-process call when
roles share a process, and HTTP + JSON when they're on different devices. So
**moving a role to another device is a transport swap, not a rewrite** — and
anyone can supply their own implementation of any role (a phone as the Brain, a
Jetson running a local model as the Classifier, a custom Actuator).

We build **laptop-first, hardware-last** — prove the whole loop where iteration
is instant, then re-host roles onto constrained hardware:

| | Sensor | Classifier | Brain | Actuator |
| --- | --- | --- | --- | --- |
| ① Laptop *(now)* | USB webcam | hosted Claude | laptop | USB-UIRT / LIRC |
| ② Raspberry Pi | Pi cam / webcam | Claude / local | Pi | Pi GPIO |
| ③ ESP32 | **ESP32** camera | on server | Pi / server | Pi or ESP32 |
| ④ Phone *(later)* | phone cam | on-phone / hosted | **phone** | networked blaster |

The concept has been validated against hosted vision models (Claude/Gemini/ChatGPT
reliably tell a baseball broadcast from a commercial); the pluggable Classifier
seam is what lets that move to a local model later. See `docs/architecture.md` for
the full contracts, decision state machine, and roadmap.

## Repo layout

| Path | What |
| --- | --- |
| `docs/architecture.md` | **Canonical design** — roles, contracts, roadmap. Start here. |
| `docs/phase1-kickoff.md` | Copy-paste prompt to start Phase 1 in a fresh context. |
| `server/` | Python (FastAPI). The Brain + Classifier + admin portal; refactoring into the role structure for Phase 1. |
| `firmware/` | C++ (ESP32-S3). The **Phase 3** Sensor (dumb capture → POST). Built and ran end-to-end; tabled until the laptop/Pi loop is proven. |
| `docs/hardware-prototype.md`, `docs/stage1-*.md` | ESP32-era plans — superseded, kept as Phase 3 reference. |

> Firmware is C++ because the ESP32 camera/IR/display libraries are C/C++; the
> server language (Python) is a free choice.

## Status

**Phase 1 — laptop-first.** The `server/` brain (classifier, decision engine,
admin portal) is implemented and has classified live broadcast frames correctly.
The ESP32 firmware skeleton was built and demonstrated end-to-end, then **tabled
to Phase 3** in favor of proving the full see→decide→act loop on the laptop with a
USB webcam and a USB-UIRT IR blaster. See `docs/architecture.md` §9.

## License

Code is licensed under the **Apache License 2.0** — see [`LICENSE`](./LICENSE) and
[`NOTICE`](./NOTICE). The "AdalogHole" name and branding are not covered by the
license. Hardware/CAD files (added later) will carry their own open-hardware
license (e.g. CERN-OHL or CC-BY).

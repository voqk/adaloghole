# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 📐 **Read [`docs/architecture.md`](docs/architecture.md) first — it is the canonical design.**
> The project has pivoted to a **laptop-first, hardware-last** strategy built
> around five pluggable roles (Sensor, Classifier, Brain, Actuator, Controller).
> The ESP32-first material below and in `docs/hardware-prototype.md` /
> `docs/stage1-*.md` is **tabled to Phase ③** (see the banners on those docs) and
> describes the *future* device tier, not current active work.

## What this is

AdalogHole is an open-source device that watches a TV with a camera and mutes commercials via IR ("the analog hole") during live sports. The design is **five pluggable roles** — Sensor → Classifier → Brain → Actuator → Controller — each defined by a contract, not an implementation; see [`docs/architecture.md`](docs/architecture.md) for the canonical treatment.

The `server/` code is **implemented** (classifier, decision engine, admin portal — it has classified live broadcast frames correctly), and the ESP32 `firmware/` skeleton was built and demonstrated end-to-end. The project has since pivoted to **laptop-first, hardware-last**: Phase 1 refactors `server/` into the role structure and closes the whole loop on the laptop (USB webcam Sensor + USB-UIRT/LIRC Actuator) before re-hosting roles onto a Pi, then an ESP32. Start Phase 1 from [`docs/phase1-kickoff.md`](docs/phase1-kickoff.md).

## Architecture

Canonical treatment: [`docs/architecture.md`](docs/architecture.md). In short — five
roles, each a contract with two bindings (an in-process call when roles share a
process; HTTP + JSON when they're on different devices), so moving a role to another
device is a transport swap, not a rewrite:

1. **Sensor** — grabs a frame on a cadence and submits it to the Brain. Phase 1: a Python/OpenCV webcam. Phase 3: the ESP32 `firmware/` (dumb capture → POST).
2. **Classifier** — frame (+optional context) → `{label, confidence, reason}`. *Pluggable inference*; its prompt/model/key are private to the implementation. Phase 1: hosted Claude. Later: a local model (e.g. on a Jetson).
3. **Brain** — the hub (`server/`): runs the decision state machine, owns state + generic settings, calls the Classifier, emits Commands.
4. **Actuator** — Command → IR (mute/unmute/soundbar). Phase 1: USB-UIRT via LIRC. Phase 2: Pi GPIO. Phase 3: optionally the ESP32.
5. **Controller/UI** — override knob + status display + admin portal.

**No secrets in the open-source build.** The Anthropic key is Classifier-private config, stored server-side (`data/settings.json`, gitignored), never in firmware. The Phase 3 device only gets Wi-Fi creds + the server URL (in `firmware/include/config.h`, copied from `config.example.h`, gitignored).

### Request flow (Brain frame-intake, the `/frame` seam — currently `/classify`)

`Sensor → POST (raw JPEG body) → classifier.classify_frame() → {label, confidence, reason} → DecisionEngine.feed(label) → {action: mute|unmute|none, muted} → JSON back`. The same contract serves an in-process Sensor (Phase 1) and a remote ESP32 Sensor (Phase 3) unchanged.

Key server pieces:
- `app/classifier.py` — calls Claude with **structured output** (`output_config.format` json_schema), **not** tool/function calling; we only want a typed JSON verdict back.
- `app/decision.py` — `DecisionEngine`, the tunable core. Hysteresis: require N consecutive same-label frames (`flip_threshold`) before flipping mute state; `unknown` holds current state. One shared instance (single TV).
- `app/settings.py` — pydantic config persisted to `data/settings.json`, edited live from the admin portal (key, model, program description, system prompt template with `{program}`, thresholds, sample interval).

## Commands

### Server (`server/`)
```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Device endpoint: `POST http://<server-ip>:8000/classify` (body = JPEG)
- Admin portal: `http://<server-ip>:8000/admin`
- Interactive API docs: `http://<server-ip>:8000/docs`

### Firmware (`firmware/`)
Uses PlatformIO (board `seeed_xiao_esp32s3`). Before building, copy `include/config.example.h` to `include/config.h` and fill in Wi-Fi + server URL.
```sh
pio run                 # build
pio run -t upload       # flash
pio device monitor      # serial @ 115200
```

## Conventions / gotchas

- **Default model is `claude-opus-4-8`**, but for this frequent, simple classification `claude-sonnet-4-6` / `claude-haiku-4-5` are much cheaper and adequate — the model is switchable from the admin portal. Consult the `claude-api` skill before touching model IDs or the Anthropic call.
- The ESP32 build **requires PSRAM** (`-DBOARD_HAS_PSRAM`, `memory_type = qio_opi`) to hold the JPEG + build the request body.
- Firmware is C++ only because the ESP32 camera/IR/display libs are C/C++; the server language (Python) is a free choice.
- Code is Apache-2.0; the "AdalogHole" name/branding is not covered by the license.

## Build plan (see `docs/architecture.md` §9)

**Laptop-first, hardware-last.** The same five roles get re-hosted across tiers;
only where each runs (and which seams cross the wire) changes:

- **Phase ① (active): laptop.** All roles in one Python deployment. Sensor = USB
  webcam at the TV; Classifier = hosted Claude; Actuator = USB-UIRT over LIRC.
  Full closed loop (see ad → mute the real TV). Factor `server/` into the role
  structure; keep the `/frame` (née `/classify`) contract stable.
- **Phase ②: Raspberry Pi** — re-host the same roles onto one cheap box on the
  Wi-Fi; IR via Pi GPIO or the USB-UIRT.
- **Phase ③: ESP32 Sensor** — the tabled `firmware/` slots back in here (the
  original dumb-device architecture), plus enclosure.
- **Phase ④ (later): phone as Brain.**

The guiding principle is unchanged — the risky part is the classifier, not the
hardware — but we now prove the whole loop on the laptop before touching
constrained hardware. **Tabled (Phase ③ reference only):**
`docs/hardware-prototype.md`, `docs/stage1-core-loop-plan.md`,
`docs/stage1-handoff-next-session.md`.

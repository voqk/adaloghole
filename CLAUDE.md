# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AdalogHole is an open-source device that watches a TV with a camera and mutes commercials via IR ("the analog hole"). The repo is currently **skeletons only** — nearly every source file is a documented stub (`raise NotImplementedError`, `// TODO`, empty function bodies). The TODO comments in each stub are the spec; implement against them rather than inventing new structure.

## Architecture

Three tiers, deliberately split so the open-source build ships **no secrets**:

1. **`firmware/`** (C++ / Arduino / PlatformIO, on an ESP32-S3 camera board) — pure I/O. Captures a JPEG on a timer, POSTs it over plain HTTP (no TLS, no API key) to the LAN server, reads back `{action, muted}`, fires IR, drives a knob + LCD. **No ML and no decision logic on the device.**
2. **`server/`** (Python / FastAPI, runs on the user's LAN) — the "brain." Holds the user's Anthropic key + prompt (entered via an admin portal), calls the Claude vision API to classify each frame, runs debounce logic, returns the action.
3. **Claude vision API** — does the actual program-vs-commercial classification.

The Anthropic key lives **only on the server** (in `data/settings.json`, gitignored), never in firmware. The device only gets Wi-Fi creds + the server URL (in `firmware/include/config.h`, copied from `config.example.h`, gitignored).

### Request flow

`ESP32 → POST /classify (raw JPEG body) → classifier.classify_frame() → {label, confidence, reason} → DecisionEngine.feed(label) → {action: mute|unmute|none, muted} → JSON back to device`.

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

## Build plan (see `docs/hardware-prototype.md`)

Stage 0 (done): validate the vision classifier with saved frames, zero hardware. Stage 1: XIAO Sense + IR emitter → minimal capture→classify→mute loop. Stage 2: add encoder override + LCD. Stage 3: untether (LiPo) + enclosure. The guiding principle: the risky part is the classifier, not the hardware — keep the ESP32 dumb.

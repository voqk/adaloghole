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

## Run it (Phase 1: everything on one laptop)

You need Python 3.11+, a webcam, and an Anthropic API key. IR hardware is
optional — without it the loop runs "log-only" and prints the mute/unmute
commands it *would* fire.

```sh
git clone <this repo> && cd adaloghole/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

That one command starts the whole loop: the webcam Sensor autostarts and POSTs
a frame to the Brain every few seconds. Then:

1. **Enter your API key** — open `http://localhost:8000/admin`, paste your
   Anthropic key into the Claude classifier section, set the **program
   description** to what you're watching (e.g. "a live baseball game"), save.
   Edits apply on the next frame; no restart.
2. **Aim the camera at the TV** — the most recent captured frame is written to
   `server/data/last_frame.jpg` (overwritten every frame); eyeball it while
   aiming. Using a **USB camera** instead of the built-in one? Set its
   `/dev/video<N>` index in `server/adaloghole.toml`:
   ```toml
   [sensor.webcam]
   device = 2        # find yours with: v4l2-ctl --list-devices
   ```
3. **Watch it decide** — the server log shows every verdict; `/admin` shows the
   live A/V state, and the override knob forces mute/unmute or locks the current
   state anytime.
4. **Make it mute the real TV** — plug in a USB-UIRT (or any LIRC-supported IR
   blaster), follow [`docs/lirc-setup.md`](docs/lirc-setup.md) to learn your
   TV's mute code, then set `actuator = "lirc"` in `server/adaloghole.toml`.

Everything about which implementation fills each role lives in
`server/adaloghole.toml` — e.g. `classifier = "static"` runs the loop with no
key and no network for testing. More detail (endpoints, running the sensor as a
separate process, the test suite) in [`server/README.md`](server/README.md).

## Repo layout

| Path | What |
| --- | --- |
| `docs/architecture.md` | **Canonical design** — roles, contracts, roadmap. Start here. |
| `docs/phase1-kickoff.md` | Copy-paste prompt to start Phase 1 in a fresh context. |
| `server/` | Python (FastAPI). All five roles for Phase 1: webcam Sensor, Claude Classifier, Brain, LIRC/log-only Actuator, admin portal. Wired from `server/adaloghole.toml`. |
| `docs/lirc-setup.md` | One-time IR hardware setup (LIRC + USB-UIRT + irrecord). |
| `firmware/` | C++ (ESP32-S3). The **Phase 3** Sensor (dumb capture → POST). Built and ran end-to-end; tabled until the laptop/Pi loop is proven. |
| `docs/hardware-prototype.md`, `docs/stage1-*.md` | ESP32-era plans — superseded, kept as Phase 3 reference. |

> Firmware is C++ because the ESP32 camera/IR/display libraries are C/C++; the
> server language (Python) is a free choice.

## Status

**Phase 1 — laptop loop running.** The five-role refactor is done: webcam
frames flow to the Brain over localhost HTTP, Claude classifies them live, the
decision state machine debounces (with an override knob in the portal), and
Commands fire through the Actuator seam. The only piece pending hardware is the
IR blaster itself — until the USB-UIRT is set up (`docs/lirc-setup.md`), the
log-only actuator prints what it would fire. The ESP32 firmware skeleton was
built and demonstrated end-to-end earlier, then **tabled to Phase 3**; it
rejoins unchanged via the preserved `POST /classify` contract. See
`docs/architecture.md` §9.

## License

Code is licensed under the **Apache License 2.0** — see [`LICENSE`](./LICENSE) and
[`NOTICE`](./NOTICE). The "AdalogHole" name and branding are not covered by the
license. Hardware/CAD files (added later) will carry their own open-hardware
license (e.g. CERN-OHL or CC-BY).

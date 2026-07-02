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

The **Phase 1 refactor is done**: `server/` implements the five roles behind `Protocol`/ABC contracts, selected at startup from `server/adaloghole.toml` (registry + factory, see `app/registry.py` / `app/bootstrap.py`). The laptop loop runs end-to-end: webcam Sensor → localhost HTTP `/frame` → Claude Classifier → Brain state machine → Actuator. The Actuator defaults to log-only (`none`) until the USB-UIRT arrives — then follow [`docs/lirc-setup.md`](docs/lirc-setup.md) and flip `actuator = "lirc"` in the toml. The ESP32 `firmware/` skeleton (built and demonstrated end-to-end earlier) rejoins in Phase 3 via the preserved `/classify` alias.

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

**No secrets in the open-source build.** The Anthropic key is Classifier-private config, stored server-side (`data/classifier_claude.json`, gitignored), never in firmware or in `adaloghole.toml`. The Phase 3 device only gets Wi-Fi creds + the server URL (in `firmware/include/config.h`, copied from `config.example.h`, gitignored).

### Request flow (Brain frame-intake, the `/frame` seam)

`Sensor → POST /frame (raw JPEG body + X-Adaloghole-* meta headers) → Classifier.classify(frame, Context) → Verdict{label: content|commercial|unknown, confidence, reason} → DecisionStateMachine.feed(verdict) → Command? → Actuator.execute → FrameResponse{verdict, status, command?}`. The legacy `POST /classify` alias returns the flat `{label, confidence, reason, action, muted}` shape the ESP32 firmware parses — keep it stable so the Phase 3 device rejoins unchanged. (Wire label is `content`; the Claude classifier's model-facing "program" vocabulary is mapped privately.)

Key server pieces (all under `server/app/`):
- `contracts.py` — the §4 data contracts (pydantic): Frame/Context/Verdict/Command/Ack/Capabilities/Control/Status/GenericSettings.
- `roles/classifier/claude.py` — calls Claude with **structured output** (`output_config.format` json_schema), **not** tool/function calling; key/model/prompt live in `data/classifier_claude.json` behind the `AdminConfigurable` protocol. `roles/classifier/static.py` is the no-network test double.
- `roles/brain/` — `debounce.py` (`DecisionEngine` hysteresis: N consecutive same-label frames before flipping; `unknown` holds), `state_machine.py` (adds `mode` auto/override/locked + `av_state`; Commands on change only), `core.py` (the Brain hub). Not thread-safe by design — verdicts feed on the event loop only.
- `roles/sensor/webcam.py` — OpenCV; owns the cadence (re-reads `GET /settings` each loop); runs as a lifespan daemon thread (`autostart`) or standalone process. Always talks real localhost HTTP.
- `roles/actuator/` — `none.py` (log-only default) and `lirc.py` (`irsend` shell-out; failures return `Ack(ok=False)`, never raise into the Brain).
- `settings_store.py` — generic Settings (`data/settings.json`) + the one-time migration from the old flat file.
- `routes_brain.py` — `/frame`, `/classify` (alias), `/status`, `/control`, `/settings`, `/capabilities`.
- `bootstrap.py` + `adaloghole.toml` — role selection; swap implementations (e.g. `classifier = "static"`, `actuator = "lirc"`) without code changes.

## Commands

### Server (`server/`)
```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000    # starts the whole loop (webcam sensor autostarts)
python -m pytest                                    # test suite
python -m app.roles.sensor.webcam --server http://127.0.0.1:8000   # sensor as a separate process
```
- Frame endpoint: `POST http://<server-ip>:8000/frame` (body = JPEG); `POST /classify` is the firmware-compatible alias
- Admin portal: `http://<server-ip>:8000/admin` (override knob, settings, frame test)
- Interactive API docs: `http://<server-ip>:8000/docs`
- Running uvicorn on a non-default port? Set `ADALOGHOLE_PORT` to match (the in-process sensor and logged URLs use it).
- Role wiring lives in `server/adaloghole.toml`; runtime knobs in the portal.

### Firmware (`firmware/`)
Uses PlatformIO (board `seeed_xiao_esp32s3`). Before building, copy `include/config.example.h` to `include/config.h` and fill in Wi-Fi + server URL.
```sh
pio run                 # build
pio run -t upload       # flash
pio device monitor      # serial @ 115200
```

## Conventions / gotchas

- **The classifier defaults to `claude-haiku-4-5`** — the cheapest vision model and adequate for this frequent, simple classification; Sonnet/Opus are switchable from the admin portal. Consult the `claude-api` skill before touching model IDs or the Anthropic call.
- The wire Verdict label for "the show" is `content` (architecture §4); the Claude classifier's prompt/schema use `program` internally and map it privately. Don't leak model-facing vocabulary across the seam.
- The ESP32 build **requires PSRAM** (`-DBOARD_HAS_PSRAM`, `memory_type = qio_opi`) to hold the JPEG + build the request body.
- Firmware is C++ only because the ESP32 camera/IR/display libs are C/C++; the server language (Python) is a free choice.
- Code is Apache-2.0; the "AdalogHole" name/branding is not covered by the license.

## Build plan (see `docs/architecture.md` §9)

**Laptop-first, hardware-last.** The same five roles get re-hosted across tiers;
only where each runs (and which seams cross the wire) changes:

- **Phase ① (active): laptop.** All roles in one Python deployment. Sensor = USB
  webcam at the TV; Classifier = hosted Claude; Actuator = USB-UIRT over LIRC.
  **Status: refactor + loop done** (see→decide→act with the log-only actuator);
  the last step is hardware — install LIRC per `docs/lirc-setup.md` when the
  USB-UIRT arrives and set `actuator = "lirc"`.
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

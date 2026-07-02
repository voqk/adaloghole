# AdalogHole server

The Phase 1 deployment: all five roles (Sensor, Classifier, Brain, Actuator,
Controller — see [`docs/architecture.md`](../docs/architecture.md)) in one
Python process on the laptop. A USB webcam watches the TV, Claude classifies
frames, the Brain debounces, and the Actuator mutes/unmutes over IR (or just
logs, until the USB-UIRT is set up).

Which implementation fills each role is chosen in **`adaloghole.toml`**.

## Layout

| Path | Role |
| --- | --- |
| `adaloghole.toml` | Role wiring: which implementation fills each role + static options. |
| `app/contracts.py` | The §4 data contracts (Frame, Verdict, Command, Status, Settings, ...). |
| `app/registry.py` / `app/bootstrap.py` / `app/config.py` | Registry + factory: toml → live role instances. |
| `app/routes_brain.py` | The Brain's HTTP surface: `/frame`, `/classify` (firmware alias), `/status`, `/control`, `/settings`, `/capabilities`. |
| `app/settings_store.py` | Generic Settings (interval, threshold, program) → `data/settings.json`. |
| `app/roles/sensor/webcam.py` | OpenCV webcam Sensor; daemon thread or standalone process. |
| `app/roles/classifier/claude.py` | Claude vision classifier (structured output). Private config (key/model/prompt) → `data/classifier_claude.json`. |
| `app/roles/classifier/static.py` | Deterministic classifier for tests/offline dev. |
| `app/roles/brain/` | Debounce core + decision state machine (mode/av_state) + the Brain hub. |
| `app/roles/actuator/none.py` | Log-only actuator (default until IR hardware arrives). |
| `app/roles/actuator/lirc.py` | `irsend` actuator — see [`docs/lirc-setup.md`](../docs/lirc-setup.md). |
| `app/roles/controller/admin.py` + `templates/admin.html` | Admin portal: override knob, status, settings, frame test. |
| `tools/classify_cli.py` | Batch-classify saved frames from the command line. |
| `tests/` | pytest suite (`.venv/bin/python -m pytest`). |

## Run

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Admin portal:     http://<server-ip>:8000/admin
# Frame endpoint:   POST http://<server-ip>:8000/frame     (body = JPEG)
# Firmware alias:   POST http://<server-ip>:8000/classify  (flat response the ESP32 parses)
# Interactive docs: http://<server-ip>:8000/docs
```

With `[sensor.webcam] autostart = true` (the default) that one command starts the
whole loop: a daemon thread grabs webcam frames and POSTs them to `/frame` over
real localhost HTTP — the same wire binding a remote Phase 3 sensor uses. If you
run uvicorn on a non-default port, set `ADALOGHOLE_PORT` to match.

To run the Sensor as a separate process instead (set `autostart = false`):

```sh
python -m app.roles.sensor.webcam --server http://127.0.0.1:8000 --device 0
```

First run creates `data/settings.json` (generic knobs) and
`data/classifier_claude.json` (your Anthropic key, model, prompt — gitignored).
Open the admin portal, paste your key, set the **program** description, save.
Edits apply on the next frame, no restart — the sensor re-reads the sample
interval from `/settings` every loop.

## Test it without hardware

```sh
# One frame, in the browser: upload it at /admin ("Test a frame")

# A folder of frames, from the CLI (run from server/):
python -m tools.classify_cli frames/*.jpg

# The firmware contract, with curl:
curl -X POST http://localhost:8000/classify \
     -H "Content-Type: image/jpeg" --data-binary @frame.jpg
# -> {"label":"...","confidence":0.0,"reason":"...","action":"none|mute|unmute","muted":false}

# The full loop with no key and no camera: in adaloghole.toml set
#   classifier = "static"    and    sensor = "none"
```

Post a commercial frame twice in a row to watch the hysteresis flip (`action`
becomes `mute` on the 2nd consecutive `commercial` at the default
`flip_threshold` of 2). `unknown` verdicts hold the current state. The override
knob in `/admin` (or `POST /control`) forces/locks a state and ignores the
classifier until returned to auto.

## Model / cost note

The classifier defaults to `claude-haiku-4-5` — the cheapest option and adequate
for this coarse content-vs-commercial call. Sonnet and Opus are selectable in
the admin portal if you want more capability. Big cost levers: sample less
often (`sample_interval_s`) and downsample the frame (`[sensor.webcam] width/height`).

# AdalogHole server

The v0 "brain." Runs on your LAN. Holds the Anthropic key + prompt (set through the
admin portal), classifies frames the ESP32 POSTs to it, and returns a mute/unmute
action.

## Layout

| File | Role |
| --- | --- |
| `app/main.py` | FastAPI app; mounts the device API + admin portal. |
| `app/settings.py` | Config (key, model, prompt, program, thresholds); persisted to `data/settings.json`, edited via the portal. |
| `app/classifier.py` | Calls the Claude vision API on one frame → `{label, confidence, reason}`. |
| `app/decision.py` | Debounce/hysteresis → `mute` \| `unmute` \| `none`. The tunable core. |
| `app/routes_device.py` | `POST /classify` — the endpoint the ESP32 talks to. |
| `app/routes_admin.py` | `GET/POST /admin` — enter key, edit prompt/model/thresholds, live-test a frame. |
| `templates/admin.html` | The portal page. |
| `tools/classify_cli.py` | Stage-0: batch-classify saved frames from the command line (no hardware). |

## Run

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Device endpoint:  POST http://<server-ip>:8000/classify   (body = JPEG)
# Admin portal:     http://<server-ip>:8000/admin
# Interactive docs: http://<server-ip>:8000/docs
```

> On Debian/Ubuntu, `python -m venv` needs the `python3-venv` package. If it's
> unavailable, create the venv with `--without-pip` and bootstrap pip with
> [`get-pip.py`](https://bootstrap.pypa.io/get-pip.py).

First run creates `data/settings.json` (gitignored — it holds your API key). Open the
admin portal, paste your Anthropic key, set the **program** description, and save.

## Test it without the ESP32 (Stage 0)

The risky part is the vision classifier, and you can validate it with saved frames and
zero hardware:

```sh
# One frame, in the browser: upload it at http://<server-ip>:8000/admin (Test a frame)

# A folder of frames, from the CLI (run from server/):
python -m tools.classify_cli frames/*.jpg

# The full device contract, with curl:
curl -X POST http://localhost:8000/classify \
     -H "Content-Type: image/jpeg" --data-binary @frame.jpg
# -> {"label":"...","confidence":0.0,"reason":"...","action":"none|mute|unmute","muted":false}
```

Post a commercial frame twice in a row to watch the hysteresis flip (`action` becomes
`mute` on the 2nd consecutive `commercial` at the default `flip_threshold` of 2).

## Model / cost note

`app/settings.py` defaults the model to `claude-haiku-4-5` — the cheapest option and
adequate for this coarse program-vs-commercial call. `claude-sonnet-4-6` and
`claude-opus-4-8` are also selectable in the admin portal if you want more capability.
Big cost levers: sample less often and downsample the frame.

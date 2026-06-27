# AdalogHole server

The v0 "brain." Runs on your LAN. Holds the Anthropic key + prompt (set through the
admin portal), classifies frames the ESP32 POSTs to it, and returns a mute/unmute
action. **Skeleton only — not implemented yet.**

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

## Run (once implemented)

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Device endpoint:  POST http://<server-ip>:8000/classify   (body = JPEG)
# Admin portal:     http://<server-ip>:8000/admin
# Interactive docs: http://<server-ip>:8000/docs
```

## Model / cost note

`app/settings.py` defaults the model to `claude-opus-4-8`. For this frequent,
simple classification, `claude-sonnet-4-6` and `claude-haiku-4-5` are much cheaper
and handle it well — switchable in the admin portal. Big cost levers: sample less
often, downsample the frame, and let the mic "second opinion" gate when to call the
API at all.

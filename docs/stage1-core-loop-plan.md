# AdalogHole — Stage 1 core loop (multi-context handoff plan)

## Context

The XIAO ESP32-S3 Sense, LiPo battery, and microSD have arrived. The doc
`docs/hardware-prototype.md` calls the capture → classify → mute loop the real
de-risk ("real OV2640 frames lie less than phone-camera frames"). The **server
brain is already implemented** (`classifier.py`, `decision.py`,
`routes_device.py`) and `camera.cpp` is done. What's missing is the firmware
glue that gets a real sensor frame to the server and reads the verdict back.

This plan delivers **only the now-unblocked core loop**:
`config.h → camera_capture() → POST /classify → {action, muted} → serial`.
IR and UI are left as compilable no-op stubs — their hardware (TSOP IR receiver,
rotary encoder, status display) hasn't arrived and the display model is still an
open question in the doc. They get their own plan later.

**Execution model:** sequential handoff. One context does a stage, verifies its
checkpoint, then hands off. Each stage below lists the files it owns, the work,
and the green-light checkpoint the next context can assume is true.

**Decision: dev + server both live on the Linux laptop.** The ESP32 flashes over
native `/dev/ttyACM0` (no WSL `usbipd-win`), and the server binds the laptop's LAN
IP so the device can reach it over Wi-Fi (no WSL NAT / `netsh portproxy`). The
work moves off this WSL box after Stage 0 below.

**Make this plan discoverable first (Stage 0, done on this WSL repo now).** This
file lives in plan-mode scratch (`~/.claude/plans/`), which a fresh context won't
find. Before anything moves, copy it into the repo as
`docs/stage1-core-loop-plan.md` (alongside `hardware-prototype.md`) and add a
one-line pointer from the "Build plan" section of `CLAUDE.md`. Because it now
lives in the repo, it travels with the copy to the laptop, and each later stage
records its checkpoint result in it (a "Status:" line per stage) so the next
context reads current state, not stale instructions.

## Current state (verified)

| Piece | Status |
| --- | --- |
| `server/app/*` (classifier, decision, routes_device, admin) | ✅ implemented; `.venv` exists; `data/settings.json` present, **`api_key` empty** |
| `firmware/src/camera.{h,cpp}` | ✅ done — `bool camera_init()`, `camera_fb_t *camera_capture()`, `void camera_return(camera_fb_t*)`, XIAO pin map, SVGA JPEG, exposure locked to `CAM_*` macros |
| `firmware/src/net.{h,cpp}` | ⬜ stub |
| `firmware/src/main.cpp` | ⬜ stub |
| `firmware/src/ir.{h,cpp}`, `ui.{h,cpp}` | ⬜ stub (deferred this plan) |
| `firmware/include/config.h` | ⬜ not created (only `config.example.h`) |
| `firmware/platformio.ini` | `lib_deps` commented out |
| PlatformIO toolchain | not installed (installed on the Linux laptop in Stage M) |

## Hardware availability

- **Now:** XIAO ESP32-S3 Sense, LiPo, microSD. IR emitter on hand.
- **Not arrived:** TSOP38238 IR receiver (needed to *learn* codes), rotary
  encoder, status display. → IR + UI are out of scope here.

## Dependencies & toolchain (verified)

- **Server Python deps — already installed** in `server/.venv` (`anthropic 0.112.0`,
  `fastapi`, `uvicorn`, `pydantic`, `jinja2`, `python-multipart`). Stage C does
  **not** need `pip install`; just set the key and run uvicorn.
- **ArduinoJson — no manual install.** Declared in `platformio.ini` `lib_deps`;
  PlatformIO fetches it on first build (pypi/registry reachable, confirmed).
- **PlatformIO — the one real install, on the Linux laptop.** Install with
  `pipx install platformio` (isolated; or the PlatformIO VS Code extension). One
  time: `sudo usermod -aG dialout $USER` then re-login, so flashing
  `/dev/ttyACM0` works without sudo. First `pio run` downloads the `espressif32`
  platform + toolchain (~hundreds of MB) and the `ArduinoJson` lib automatically.

## The contract (lock this; every stage depends on it)

**HTTP — `POST /classify`** (from `server/app/routes_device.py`):
- Request: method `POST`, raw JPEG bytes as body, header `Content-Type: image/jpeg`.
- Response JSON: `{ "label": "program|commercial|unknown", "confidence": <0..1>,
  "reason": <str>, "action": "mute|unmute|none", "muted": <bool> }`.
- Firmware acts on **`action`** (string) and displays **`muted`**. All debounce
  lives server-side in `DecisionEngine`.

**Firmware `net.h` — finalize the Result struct so `main.cpp` compiles:**
```c
struct Result {
  enum Action { NONE, MUTE, UNMUTE } action;
  bool muted;
  bool ok;            // false on Wi-Fi/HTTP/parse failure -> main holds state, fires no IR
};
bool   net_connect_wifi();
Result net_classify(camera_fb_t *fb);   // POST fb->buf/fb->len, parse reply
```
`net_classify` maps the server's `action` **string** onto the enum
(`"mute"→MUTE`, `"unmute"→UNMUTE`, else `NONE`).

---

## Stage 0 — Make the plan discoverable (this WSL context, now)

**Owns:** `docs/stage1-core-loop-plan.md` (new), `CLAUDE.md`.

1. Copy this plan into the repo at `docs/stage1-core-loop-plan.md`.
2. Add a one-line pointer to it from the "Build plan" section of `CLAUDE.md`.

**Checkpoint:** the plan is committed in the repo so it travels with the copy to
the laptop and every later context can read/update it.

**Status: ✅ done (2026-06-29, on the WSL box).** This doc lives at
`docs/stage1-core-loop-plan.md`; the `CLAUDE.md` "Build plan" section points to
it. Next: Stage M on the Linux laptop.

---

## Stage M — Migrate dev + server to the Linux laptop

**Owns:** the laptop environment (no repo source changes).

1. Get the repo onto the laptop. It's already a git repo (root
   `/home/hunter/source/adaloghole/adaloghole`, latest commit on `main`), and
   `.venv/`, `data/settings.json`, and `config.h` are gitignored — so a plain
   `git clone` carries exactly the right files and none of the secrets. Push to a
   remote (or `git bundle`) here, then clone on the laptop. (rsync / microSD also
   work but clone is cleanest and gives commit history + rollback.)
2. Recreate the server venv on the laptop:
   `cd server && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
3. Install the firmware toolchain: `pipx install platformio`; then
   `sudo usermod -aG dialout $USER` and re-login.
4. Plug in the XIAO and confirm it enumerates: `ls /dev/ttyACM*` (or `ttyUSB*`).

**Checkpoint:** on the laptop, `pio --version` works, the board shows up under
`/dev/`, and `server/.venv` has the deps. All remaining stages run here.

**Status: ✅ mostly done (2026-06-29, on the Linux laptop `xps`, LAN IP
192.168.1.193).** This repo IS the laptop clone. `server/.venv` recreated with all
deps (anthropic, fastapi, uvicorn 0.49.0, pydantic-settings, python-multipart).
PlatformIO Core 6.1.19 installed in an isolated venv `~/.platformio-venv` (no
sudo / no `pipx` needed) and symlinked into `~/.local/bin` (on PATH) — functionally
equivalent to the planned `pipx install`. **Two items deferred to Stage D (not
blocking A/B/C):** (a) `sudo usermod -aG dialout $USER` + re-login — handed to the
user, needs sudo + a fresh login; (b) the XIAO isn't plugged in yet (no
`/dev/ttyACM*`).

---

## Stage A — Skeleton that compiles (no hardware)

**Owns:** `net.h`, `ir.cpp`, `ui.cpp`, `main.cpp`, `platformio.ini`,
`include/config.h`. Plus a throwaway compilable `net.cpp` stub.

1. Write the `net.h` contract above (Result struct + two signatures).
2. `platformio.ini`: add `lib_deps = bblanchon/ArduinoJson`
   (esp32-camera ships with the Arduino-ESP32 core; IRremote/display libs **not**
   needed yet — keep the build minimal).
3. Make `ir.cpp` and `ui.cpp` compilable no-ops: define every function declared
   in `ir.h` / `ui.h` (`ir_init`→`return true;`, `ir_send_mute/unmute`→empty,
   `ui_init`→`return true;`, `ui_update`→empty, `ui_poll_knob`→empty). This lets
   `main.cpp` link without the deferred hardware.
4. Write `main.cpp` wiring per its own TODO block:
   - `setup()`: `Serial.begin(115200); camera_init(); net_connect_wifi(); ir_init(); ui_init();`
   - `loop()`: `fb = camera_capture();` (skip iteration if null) → `r = net_classify(fb);`
     → `camera_return(fb);` → on `r.ok`: `if (r.action==Result::MUTE) ir_send_mute();`
     `else if (r.action==Result::UNMUTE) ir_send_unmute();` → `ui_update(r);`
     → `ui_poll_knob();` → `delay(SAMPLE_INTERVAL_MS);`. Also `Serial.printf` the
     action/muted each loop (this is the Stage D verification surface).
   - Provide a temporary `net.cpp`: `net_connect_wifi(){return false;}` and
     `net_classify(...){ return {Result::NONE,false,false}; }` so the project
     links. Stage B replaces it.
5. Create `include/config.h` by copying `config.example.h` (gitignored — leave
   `WIFI_*`/`SERVER_URL` as placeholders for the user to fill in Stage D).

**Checkpoint:** `cd firmware && pio run` builds and links with zero errors. No
board required. (PlatformIO was installed in Stage M.)

**Status: ✅ done (2026-06-29).** `pio run` → SUCCESS (74s, first build downloads
toolchain; RAM 7.0%, Flash 9.4%). Wrote: `net.h` (Result struct + 2 signatures per
the contract), `main.cpp` (full capture→classify→IR→ui loop with a per-loop
`Serial.printf` verification line), `ir.h`/`ir.cpp` + `ui.h`/`ui.cpp` (compilable
no-ops — prototypes added to the headers, which previously held only TODO comments,
so `main.cpp` links), `platformio.ini` (`lib_deps = bblanchon/ArduinoJson`, IR/display
libs left out), temporary `net.cpp` link stub, and `include/config.h` (copied from
`config.example.h`, gitignored, placeholders).

---

## Stage B — Real networking (`net.cpp`)

**Owns:** `net.cpp` only (replaces the Stage A stub).

1. `net_connect_wifi()`: `WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);`
   loop on `WiFi.status() != WL_CONNECTED` with a timeout + serial dots; return
   the connected bool.
2. `net_classify(camera_fb_t *fb)`:
   - `HTTPClient http; http.begin(SERVER_URL); http.addHeader("Content-Type", "image/jpeg");`
   - `int code = http.POST(fb->buf, fb->len);`
   - On `code == 200`: parse body with `ArduinoJson` (`JsonDocument`), read
     `action` (string) and `muted` (bool), map string→`Result::Action`, set `ok=true`.
   - On non-200 / parse error: return `{NONE, false, ok=false}` and serial-log the code.
   - `http.end();`
3. Keep the JPEG sizing in mind: SVGA quality-12 frames fit a normal POST; PSRAM
   is already enabled (`-DBOARD_HAS_PSRAM`, `qio_opi`).

**Checkpoint:** `pio run` still builds. On-device network verification is
deferred to Stage D (needs the server from Stage C and real creds).

**Status: ✅ done (2026-06-29).** `pio run` → SUCCESS (5.3s incremental; RAM 15.2%,
Flash 27.5%). `net.cpp` implements `net_connect_wifi()` (STA mode, 20s timeout with
serial dots) and `net_classify()` (HTTPClient POST `image/jpeg`, ArduinoJson 7
`JsonDocument` parse, action-string→enum, `ok=false` on any Wi-Fi/HTTP/parse failure
so the caller holds state). On-device verification still deferred to Stage D.

---

## Stage C — Server bring-up (no firmware)

**Owns:** server runtime only — touches no firmware files; can run any time
after Stage A.

1. Venv recreated in Stage M. `cd server && source .venv/bin/activate`.
2. Start it: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`. Note the
   **device endpoint URL** it logs (`http://<laptop-lan-ip>:8000/classify`) —
   that's the `SERVER_URL` for `config.h`. Find the laptop's LAN IP with
   `ip addr` / `hostname -I` if needed, and allow port 8000 through its firewall.
3. Open `http://<lan-ip>:8000/admin`, paste the Anthropic **api_key**, confirm
   model (`claude-haiku-4-5` is set and is the cheap/adequate default for this).
4. Sanity-check the classifier with no hardware:
   `python -m tools.classify_cli path/to/saved-frame.jpg` → prints
   `{label, confidence, reason}`.

**Checkpoint:**
`curl --data-binary @frame.jpg -H 'Content-Type: image/jpeg' http://<lan-ip>:8000/classify`
returns valid `{label,confidence,reason,action,muted}` JSON.

---

## Stage D — Integrate, flash, tune camera (the de-risk)

**Owns:** `include/config.h` (fill secrets), and the physical board + TV.
Depends on A + B + C green.

1. Fill `config.h`: real `WIFI_SSID`/`WIFI_PASSWORD` and `SERVER_URL` from Stage C.
2. `pio run -t upload` then `pio device monitor` (115200). Confirm Wi-Fi connects
   and each loop logs an `action`/`muted` line.
3. **Tune exposure in the real room** (per `docs/hardware-prototype.md` Stage 1):
   point the camera at the TV under the lights you actually watch in. Grab a
   frame; if the screen is blown white → **lower** `CAM_AEC_VALUE`; too dark →
   **raise** it. Keep `CAM_AGC_VALUE` near 0. Set `CAM_VFLIP`/`CAM_HMIRROR` to
   match mounting. Reflash, repeat until screen content is legible.
4. Run real OV2640 frames through the loop during a live broadcast; verify the
   server logs `POST /classify` and the device serial shows sensible
   `program`/`commercial` verdicts and `action` flips after `flip_threshold` (2)
   consecutive frames.

**Checkpoint:** end-to-end loop confirmed on real hardware — the device captures,
the server classifies real sensor frames correctly across program vs. commercial,
and `action`/`muted` land back on the device. IR firing is a no-op (expected;
deferred).

---

## Verification (end-to-end)

- **Build green, no board:** `cd firmware && pio run` after Stage A and after Stage B.
- **Server alone:** `classify_cli` on a saved frame + the `curl` POST above (Stage C).
- **Full loop, on hardware:** Stage D — device serial shows `action`/`muted`,
  server log shows `POST /classify` 200s, verdicts track program vs. commercial.

## Out of scope (next plan)

- `ir.cpp` real implementation (`IRremoteESP8266`, learn via TSOP38238, persist
  codes to NVS/SD) — blocked until the IR receiver arrives.
- `ui.cpp` (rotary encoder override + status LCD) — blocked on hardware **and**
  the open question in `docs/hardware-prototype.md`: confirm the display model
  (LilyGo T-Display-S3 vs. a small I2C OLED) before starting. That choice picks
  the display lib (LovyanGFX / TFT_eSPI vs. an OLED driver).
- Untether (LiPo runtime) + enclosure — Stage 3.

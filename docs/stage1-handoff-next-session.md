# Stage 1 core loop — session handoff (resume here)

Hand this to the next Claude session. It captures live state after a machine
reboot. **First read `docs/stage1-core-loop-plan.md`** — it has a `Status:` line
per stage; this file is the short "where we are right now / what's next" pointer.

## Environment (already set up, survives reboot)
- **Machine:** native Linux laptop, host `xps` (NOT WSL). LAN IP **192.168.1.193**.
- **Repo:** `/home/hunter/source/adaloghole/adaloghole`, branch `main`,
  HEAD = `570a314` (Stages A/B committed). Not pushed to `origin` yet.
- **PlatformIO:** Core 6.1.19 in isolated venv `~/.platformio-venv`, symlinked to
  `~/.local/bin/pio` (on PATH — `pio` just works). First build already downloaded
  the espressif32 toolchain, so `pio run` is fast now.
- **Server venv:** `server/.venv` has all deps (anthropic, fastapi, uvicorn,
  pydantic-settings, python-multipart).
- **Gitignored (don't commit):** `firmware/include/config.h`,
  `server/data/settings.json`, `*/.venv/`.

## Done ✅
- **Stage M** (env migration to laptop) — venv + PlatformIO installed.
- **Stage A** (skeleton compiles) — `net.h` contract, `main.cpp` loop, no-op
  `ir`/`ui`, `platformio.ini` (`lib_deps = bblanchon/ArduinoJson`), gitignored
  `config.h`. `pio run` → green.
- **Stage B** (real networking) — `net.cpp`: STA Wi-Fi (20s timeout), HTTPClient
  POST `image/jpeg`, ArduinoJson parse of `{action, muted}`, `ok=false` holds
  state on any failure. `pio run` → green.
- **Stage C (partial)** — server boots on `192.168.1.193:8000`; root→/admin,
  `/admin` & `/docs` return 200; `data/settings.json` bootstrapped with
  `model: claude-haiku-4-5` and **empty `api_key`**.

## Just-rebooted check (do this first)
The reboot was to activate `dialout` group membership (needed to flash the board).
`usermod` already ran — `getent group dialout` lists `hunter`. After reboot, confirm
the *active* session now has it:
```sh
id -nG | tr ' ' '\n' | grep -x dialout && echo "ready to flash"
```

## Remaining work
### Finish Stage C (needs the Anthropic API key)
1. Start the server:
   ```sh
   cd server && source .venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Open `http://192.168.1.193:8000/admin`, paste the **Anthropic api_key**
   (model `claude-haiku-4-5` is already the cheap/adequate default — fine to keep).
3. Sanity-check the classifier with a saved frame (no hardware):
   ```sh
   python -m tools.classify_cli path/to/frame.jpg        # from server/, venv active
   curl --data-binary @frame.jpg -H 'Content-Type: image/jpeg' \
     http://192.168.1.193:8000/classify                  # expect {label,confidence,reason,action,muted}
   ```

### Stage D — flash + tune + verify (needs the XIAO + a TV)
1. Plug in the XIAO; confirm it enumerates: `ls /dev/ttyACM*` (or `ttyUSB*`).
2. Fill `firmware/include/config.h` (gitignored, currently placeholders):
   real `WIFI_SSID` / `WIFI_PASSWORD` (2.4 GHz) and
   `SERVER_URL = "http://192.168.1.193:8000/classify"`.
3. Flash + monitor:
   ```sh
   cd firmware && pio run -t upload && pio device monitor   # 115200 baud
   ```
   Expect Wi-Fi to connect and a `[loop] ok=1 action=N muted=N` line each cycle.
4. **Tune exposure in the real room** (the actual de-risk): point the camera at the
   TV under your normal lights. Screen blown white → **lower** `CAM_AEC_VALUE`; too
   dark → **raise** it. Keep `CAM_AGC_VALUE` near 0. Set `CAM_VFLIP`/`CAM_HMIRROR`
   to match mounting. Reflash until screen content is legible.
5. During a live broadcast, verify the server logs `POST /classify` 200s and the
   device serial shows sensible `program`/`commercial` verdicts, with `action`
   flipping only after `flip_threshold` (2) consecutive same-label frames. IR firing
   is a no-op (expected — deferred to a later plan).

## Out of scope (separate later plans)
`ir.cpp` real impl (needs TSOP38238 receiver), `ui.cpp` (display + encoder; display
model still undecided), untether/enclosure. See the plan doc's "Out of scope".

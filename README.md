# AdalogHole

The product repo for **AdalogHole** — an open-source wooden wedge that watches your
TV and mutes the commercials using the "analog hole."

> Marketing site lives in the sibling `../adaloghole.com/` repo. This repo holds the
> firmware, the server/classifier, and (eventually) the CAD.

## The loop

1. **LOOK** — a wide-angle camera grabs a still frame from the TV on a timer.
2. **DECIDE** — the frame is classified: program content vs. commercial.
3. **ACT** — on a commercial, fire IR to mute the TV (or switch the soundbar);
   switch back when the program returns. A knob overrules it anytime.

## v0 architecture — LAN server, all-cloud inference

There is **no on-device ML**. The ESP32 is pure I/O. It POSTs a JPEG over plain
HTTP to a small **server on your LAN**, which holds the user's Anthropic key and
prompt (entered through an admin portal), calls the **Claude vision API**, runs the
debounce/decision logic, and returns a mute/unmute action. The ESP32 fires the IR.

```
ESP32-S3 (camera + IR + knob + LCD)         firmware/  (C++ / PlatformIO)
   │  HTTP POST  (JPEG over LAN — no key, no TLS on the device)
   ▼
AdalogHole server  ──►  Claude vision API   server/    (Python / FastAPI)
   │  { label, action: "mute" | "unmute" | "none", muted }
   ▼
ESP32-S3 fires IR
```

The key lives on the **server**, not in firmware — so an open-source build ships no
secrets, and each user enters their own key in the admin portal. The concept has
already been validated against hosted vision models (Claude/Gemini/ChatGPT reliably
tell a baseball broadcast from a commercial). Pushing inference on-device is a much
later step.

## Repo layout

| Path | Language | What |
| --- | --- | --- |
| `firmware/` | C++ (Arduino/PlatformIO) | Dumb I/O: capture a frame, POST it, fire IR, drive the knob + LCD. |
| `server/` | Python (FastAPI) | The brain + admin portal: holds the key/prompt, calls Claude vision, runs the decision logic. |
| `docs/hardware-prototype.md` | — | Bill of materials and the staged build plan. |

> Firmware is C++ because the ESP32 camera / IR / display libraries are all C/C++
> (the hardware dictates it). The server is a free choice — Python here.

## Status

Skeletons only. Nothing is implemented yet — see `docs/hardware-prototype.md` for
the staged build plan.

## License

Code is licensed under the **Apache License 2.0** — see [`LICENSE`](./LICENSE) and
[`NOTICE`](./NOTICE). The "AdalogHole" name and branding are not covered by the
license. Hardware/CAD files (added later) will carry their own open-hardware
license (e.g. CERN-OHL or CC-BY).

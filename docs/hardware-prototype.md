# AdalogHole — prototype hardware plan

Day-1 plan for getting a working prototype together fast. The guiding principle:
**the risky part is the vision classifier, not the hardware.** Keep the ESP32 as
dumb I/O and offload the thinking to a server on your LAN (see `../server/`).

## Components by function (from the product spec)

| Faces | Part | Prototype choice |
| --- | --- | --- |
| TV | Wide-angle camera | OV2640 on a camera board (see below) |
| TV | IR emitter | **Adafruit STEMMA IR transmitter** (on hand) — single LED + driver transistor; fine for a few feet line-of-sight. Beefier blaster later. |
| TV | Microphone | PDM mic onboard the XIAO ESP32-S3 Sense (loudness-spike "second opinion") |
| You | Rotary knob + push | Adafruit I2C STEMMA QT rotary encoder (2 pins) or KY-040 (3 GPIO) |
| You | Status LCD | Reuse the LilyGo T-Display-S3, or a small I2C OLED |
| Under | Battery + compute | XIAO ESP32-S3 Sense (has LiPo charging) |

## Why not the LilyGo board for the camera

The LilyGo board on hand has a screen, which is great for the "faces-you" side —
but its **parallel LCD interface uses the exact GPIOs an ESP32 DVP camera needs**,
so you can't cleanly bolt a camera onto it. And an ESP32 can't use a USB webcam;
the camera must be a DVP/SPI module wired to the camera interface. Easiest path:
do v0 on a purpose-built camera board and bring the LilyGo in later as the face.

> **TODO / open question:** confirm the exact LilyGo model (T-Display-S3?). It
> decides single-board vs. two-board firmware. Doesn't block the classifier work.

## Recommended board

**Seeed XIAO ESP32-S3 Sense (~$14)** — bundles the OV2640 camera, a PDM mic, a
microSD slot, and onboard LiPo charging. Covers three spec'd parts in one tiny
board. Alternative: **Freenove ESP32-S3-WROOM CAM (~$15)** — more broken-out
GPIO, easier breadboarding, but no mic and no battery charger.

## Bill of materials

### Buy now — core loop (camera → classify → mute)

| Item | ~Price | Status | Why |
| --- | --- | --- | --- |
| Seeed XIAO ESP32-S3 Sense | $14 | ✅ ordered | Camera + mic + battery charging. The eye + brain. |
| Adafruit STEMMA IR emitter | (on hand) | ✅ on hand | The "thumb." |
| IR receiver (TSOP38238 / VS1838B) | $2 | ✅ ordered | **Needed to *learn* the TV/soundbar codes** from the real remote. |
| Breadboard + jumpers + STEMMA QT/JST cables | ~$10 | ✅ on hand (cables TBD) | Wiring. |
| microSD card (small) | ~$8 | ✅ ordered | Buffer frames / log decisions. |

### Buy soon — human bits + untether

| Item | ~Price | Status | Why |
| --- | --- | --- | --- |
| Adafruit I2C STEMMA QT rotary encoder (#5740) + knob | ~$7 | ✅ ordered | Override knob; 2 pins. (Cheap alt: KY-040, ~$2.) |
| Status display | — | ✅ ordered | Reuse LilyGo T-Display-S3, or a small I2C OLED (~$5). |
| 3.7V LiPo (~1200 mAh, JST-PH) | ~$8 | ✅ ordered | Cut the cable. (Mind the XIAO's small battery connector.) |
| High-power IR LED + 2N2222/MOSFET (optional) | ~$2 | ⬜ optional | If the STEMMA emitter's range disappoints. |

~$35 to start, ~$60 all-in.

## Build stages

- **Stage 0 — de-risk the vision, zero hardware (do today):** point a phone/webcam
  at the TV during a real broadcast, run the `server/` classifier against saved
  frames, measure accuracy across program vs. commercial. ✅ concept already validated.
- **Stage 1 — minimal hardware loop:** XIAO Sense + IR emitter. Capture a JPEG every
  few seconds → POST to the `server/` running on your LAN → fire IR mute on the
  `"mute"` action. Range-test the emitter.

  **When the board arrives, before trusting any classifier numbers:**
  1. Copy `firmware/include/config.example.h` → `config.h`; fill in Wi-Fi + server URL.
  2. Point the camera at the real TV, **in the real room with the lights you actually
     watch in.** The OV2640's exposure is locked to a fixed guess
     (`CAM_AEC_VALUE = 300`) — it *will* be wrong for your room on the first try.
  3. Grab a frame, eyeball it: screen blown out / washed white → **lower** `CAM_AEC_VALUE`;
     too dark to read → **raise** it. Reflash, repeat until the screen content is legible.
     Keep `CAM_AGC_VALUE` near 0 (gain = noise); only raise it if max exposure is still dark.
  4. Set `CAM_VFLIP` / `CAM_HMIRROR` if the image is upside-down/mirrored from how you mount it.
  5. Only *then* run captured OV2640 frames through `server/` — phone-camera frames lie
     about real sensor quality (glare, banding, exposure). This is the de-risk that matters.
- **Stage 2 — human bits:** add the encoder for override; bring in the LCD for status.
- **Stage 3 — untether:** LiPo + charging, then the enclosure (walnut / aluminum /
  3D-printed shells).

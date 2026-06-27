#pragma once
// Copy to config.h (gitignored) and fill in. No Anthropic key here — it lives on
// the LAN server, so the device only needs Wi-Fi creds and the server URL.

#define WIFI_SSID     "your-ssid"
#define WIFI_PASSWORD "your-password"

// The AdalogHole server on your LAN. Plain HTTP — no TLS on the device.
#define SERVER_URL    "http://192.168.1.50:8000/classify"

// How often to grab and send a frame (ms). The server can also advertise this.
#define SAMPLE_INTERVAL_MS 10000

// --- Camera capture tuning (room-specific) ---
// A bright TV in a dark room makes the sensor's auto-exposure hunt and blow out
// the screen. We lock exposure/gain to fixed values instead. These are the knobs
// you'll actually tune by eye: capture a frame, check it, adjust, reflash.
#define CAM_AEC_MANUAL 1     // 1 = locked manual exposure (recommended); 0 = auto
#define CAM_AEC_VALUE  300   // fixed exposure, 0..1200 — raise if frames look dark
#define CAM_AGC_VALUE  0     // fixed gain, 0..30 — keep low; gain adds noise
#define CAM_VFLIP      0      // 1 if the board is mounted upside down
#define CAM_HMIRROR    0      // 1 to mirror horizontally

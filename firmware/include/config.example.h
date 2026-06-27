#pragma once
// Copy to config.h (gitignored) and fill in. No Anthropic key here — it lives on
// the LAN server, so the device only needs Wi-Fi creds and the server URL.

#define WIFI_SSID     "your-ssid"
#define WIFI_PASSWORD "your-password"

// The AdalogHole server on your LAN. Plain HTTP — no TLS on the device.
#define SERVER_URL    "http://192.168.1.50:8000/classify"

// How often to grab and send a frame (ms). The server can also advertise this.
#define SAMPLE_INTERVAL_MS 10000

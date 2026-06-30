// Wi-Fi + LAN server implementation.
// Plain HTTP — no TLS, no API key on the device. The server holds the secrets.
#include "net.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"

bool net_connect_wifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[wifi] connecting to %s\n", WIFI_SSID);

  const uint32_t timeout_ms = 20000;
  uint32_t start = millis();
  int last_status = -1;
  while (WiFi.status() != WL_CONNECTED && millis() - start < timeout_ms) {
    delay(500);
    int st = WiFi.status();              // 0=IDLE 1=NO_SSID 3=CONNECTED 4=CONNECT_FAILED 6=DISCONNECTED
    if (st != last_status) { Serial.printf("[wifi] status=%d\n", st); last_status = st; }
  }

  bool ok = WiFi.status() == WL_CONNECTED;
  if (ok) {
    Serial.printf("[wifi] connected, ip=%s rssi=%d\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
  }

  // Failed: ask the board what IT can see, so we know if this is RX/antenna,
  // auth, or a power brownout during the handshake.
  Serial.printf("[wifi] FAILED (last status=%d). Scanning from the board...\n", WiFi.status());
  int n = WiFi.scanNetworks();
  Serial.printf("[wifi] board sees %d networks:\n", n);
  bool saw_target = false;
  for (int i = 0; i < n; i++) {
    bool match = WiFi.SSID(i) == WIFI_SSID;
    if (match) saw_target = true;
    Serial.printf("   %s%-32s ch=%d rssi=%d enc=%d\n",
                  match ? "*> " : "   ", WiFi.SSID(i).c_str(),
                  WiFi.channel(i), WiFi.RSSI(i), WiFi.encryptionType(i));
  }
  Serial.printf("[wifi] target SSID visible to board: %s\n", saw_target ? "YES" : "NO");
  WiFi.scanDelete();
  return false;
}

// Map the server's action string onto the enum. Anything unexpected -> NONE.
static Result::Action parse_action(const char *s) {
  if (s && strcmp(s, "mute") == 0)   return Result::MUTE;
  if (s && strcmp(s, "unmute") == 0) return Result::UNMUTE;
  return Result::NONE;   // "none", missing, or unrecognized
}

Result net_classify(camera_fb_t *fb) {
  Result r = { Result::NONE, false, false };   // ok=false -> caller holds state, no IR
  if (!fb) return r;

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[net] wifi down; skipping POST");
    return r;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "image/jpeg");

  int code = http.POST(fb->buf, fb->len);
  if (code != 200) {
    Serial.printf("[net] POST failed, http=%d\n", code);
    http.end();
    return r;
  }

  String body = http.getString();
  http.end();

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, body);
  if (err) {
    Serial.printf("[net] JSON parse error: %s\n", err.c_str());
    return r;
  }

  const char *action = doc["action"];   // nullptr if the key is absent
  r.action = parse_action(action);
  r.muted  = doc["muted"] | false;
  r.ok     = true;
  return r;
}

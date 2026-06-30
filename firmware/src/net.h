#pragma once
// Wi-Fi + talking to the LAN server.
#include "camera.h"   // camera_fb_t

// One classification round-trip with the LAN server.
struct Result {
  enum Action { NONE, MUTE, UNMUTE } action;  // mapped from the server's action string
  bool muted;   // server's view of the current mute state (for the UI)
  bool ok;      // false on Wi-Fi/HTTP/parse failure -> caller holds state, fires no IR
};

bool   net_connect_wifi();
Result net_classify(camera_fb_t *fb);   // POST fb->buf/fb->len as image/jpeg, parse reply

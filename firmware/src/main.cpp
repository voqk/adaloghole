// AdalogHole firmware entry point.
//
// loop: every SAMPLE_INTERVAL_MS -> capture a JPEG -> POST to the LAN server ->
// read {action, muted} -> fire IR on mute/unmute -> update the LCD. The knob can
// override at any time. All decision logic lives on the server.

#include <Arduino.h>
#include "config.h"
#include "camera.h"
#include "net.h"
#include "ir.h"
#include "ui.h"

void setup() {
  Serial.begin(115200);
  delay(200);              // let USB-CDC settle so the first logs aren't lost
  camera_init();
  net_connect_wifi();
  ir_init();
  ui_init();
}

void loop() {
  camera_fb_t *fb = camera_capture();
  if (!fb) {               // pool starved / probe glitch — skip this round
    delay(SAMPLE_INTERVAL_MS);
    return;
  }

  Result r = net_classify(fb);
  camera_return(fb);       // hand the framebuffer back ASAP, before acting on the verdict

  if (r.ok) {              // on Wi-Fi/HTTP/parse failure we hold state and fire no IR
    if (r.action == Result::MUTE)        ir_send_mute();
    else if (r.action == Result::UNMUTE) ir_send_unmute();
  }

  // Stage D verification surface: one line per loop on the serial monitor.
  Serial.printf("[loop] ok=%d action=%d muted=%d\n", r.ok, (int)r.action, r.muted);

  ui_update(r);
  ui_poll_knob();          // manual override
  delay(SAMPLE_INTERVAL_MS);
}

// AdalogHole firmware entry point.  [STUB]
//
// loop: every SAMPLE_INTERVAL_MS -> capture a JPEG -> POST to the LAN server ->
// read {action, muted} -> fire IR on mute/unmute -> update the LCD. The knob can
// override at any time. All decision logic lives on the server.

// TODO: #include <Arduino.h>
// TODO: #include "config.h"
// TODO: #include "camera.h"  "net.h"  "ir.h"  "ui.h"

void setup() {
  // TODO: Serial.begin(115200);
  // TODO: camera_init(); net_connect_wifi(); ir_init(); ui_init();
}

void loop() {
  // TODO: frame = camera_capture();
  // TODO: result = net_classify(frame);          // {action, muted}
  // TODO: if (result.action == MUTE)   ir_send_mute();
  // TODO: if (result.action == UNMUTE) ir_send_unmute();
  // TODO: ui_update(result);
  // TODO: ui_poll_knob();                         // manual override
  // TODO: delay(SAMPLE_INTERVAL_MS);
}

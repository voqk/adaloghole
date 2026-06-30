// IR no-op stub for Stage 1 — see ir.h.
// Real learn/send (IRremoteESP8266, TSOP38238 receiver, STEMMA emitter, NVS/SD
// persistence) lands in its own plan once the IR receiver arrives.
#include "ir.h"

bool ir_init()        { return true; }
void ir_send_mute()   { /* deferred: IR emitter not wired up yet */ }
void ir_send_unmute() { /* deferred: IR emitter not wired up yet */ }

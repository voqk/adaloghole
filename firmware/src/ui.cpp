// UI no-op stub for Stage 1 — see ui.h.
// Real status LCD + rotary encoder land in Stage 2, once the display model is
// settled and the hardware arrives.
#include "ui.h"

bool ui_init()                 { return true; }
void ui_update(const Result &) { /* deferred: no display yet */ }
void ui_poll_knob()            { /* deferred: no encoder yet */ }

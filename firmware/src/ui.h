#pragma once
// Faces-you side: status LCD + rotary knob override.  (Stage 2)
// Stage 1: compilable no-ops — the real implementation is deferred until the
// display + rotary encoder arrive (see docs/stage1-core-loop-plan.md "Out of scope").
#include "net.h"   // Result

bool ui_init();
void ui_update(const Result &r);   // show current label / muted state on the LCD
void ui_poll_knob();               // rotary encoder: manual override / lock a mode

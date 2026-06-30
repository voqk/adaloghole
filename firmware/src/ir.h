#pragma once
// IR: learn the TV/soundbar codes (receiver) and send them (emitter).
// Stage 1: compilable no-ops — the real implementation is deferred until the
// TSOP38238 IR receiver arrives (see docs/stage1-core-loop-plan.md "Out of scope").

bool ir_init();
void ir_send_mute();     // replay the stored mute code (STEMMA IR emitter)
void ir_send_unmute();
// TODO: ir_learn();      // capture a code from the real remote (IR receiver)

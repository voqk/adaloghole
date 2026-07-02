# Phase 1 kickoff prompt

Copy-paste the block below into a fresh Claude Code session opened in this repo
(`/home/hunter/source/adaloghole/adaloghole`) to start Phase 1. It is deliberately
self-contained; the authoritative design it refers to is
[`architecture.md`](./architecture.md).

```text
You're starting Phase 1 of AdalogHole. Before doing anything, read
docs/architecture.md end to end — it is the canonical design and defines the five
roles, their contracts, and the laptop→Pi→ESP32→phone roadmap. Then skim CLAUDE.md.
Do NOT follow docs/hardware-prototype.md or docs/stage1-*.md — those are tabled to
Phase 3 (ESP32) and carry "SUPERSEDED" banners.

GOAL — a working closed loop entirely on this laptop:
webcam sees the TV → Classifier decides content vs. commercial → Brain debounces →
Actuator mutes/unmutes the real TV. Baseball/sports is the target content.

ARCHITECTURE — implement the five roles from architecture.md as pluggable
implementations selected at startup from config (Protocol/ABC + a registry/factory;
see §7). Phase 1 wiring:
  - Sensor     = USB webcam (Python + OpenCV), owns the sample cadence
  - Classifier = hosted Claude, structured output (output_config.format json_schema,
                 NOT tool calling). Consult the claude-api skill for model ids —
                 don't hardcode/guess. Cheap model is fine for this.
  - Brain      = local; runs the decision state machine (§6), owns state + generic
                 Settings, calls the Classifier, emits Commands
  - Actuator   = USB-UIRT via LIRC (irrecord to learn, irsend to fire). See below.
  - Controller = the existing web admin portal

KEY PRINCIPLES (from architecture.md — hold these):
  - Contracts are frozen-ish; internals are soft. Don't leak a role's guts across a seam.
  - One contract, two bindings. Run the Sensor↔Brain seam over LOCALHOST HTTP even in
    Phase 1 (it's the first seam to go remote in Phase 3) — keep it real early. Other
    seams can be in-process.
  - Keep classifier-private config (prompt, model, api key) OUT of the shared Settings
    contract — it belongs to the Claude Classifier implementation only.
  - Preserve the Brain frame-intake contract (the /frame seam, née /classify) so the
    ESP32 can rejoin unchanged in Phase 3.

REUSE, DON'T RESTART: server/ already has classifier.py, decision.py, settings.py,
routes_device.py (/classify), routes_admin.py (admin portal), tools/classify_cli.py,
and a working .venv. Phase 1 is largely REFACTORING that code into the role structure
above, then adding the webcam Sensor and the LIRC Actuator. Confirm the current
server still runs before refactoring.

HARDWARE NOTE: the USB-UIRT may not have arrived yet. Build the Actuator behind the
interface and default to a log-only "none" actuator so the see→decide loop works
today; swap in the real LIRC actuator (learn TV mute code first) once the device is
plugged in. Don't block progress on hardware.

DEFINITION OF DONE (Phase 1):
  1. Webcam frames flow to the Brain over localhost HTTP and get classified live.
  2. The decision state machine flips mute state only after flip_threshold consecutive
     same-label frames; unknown holds state.
  3. With the USB-UIRT connected, a real commercial break mutes the TV and the return
     to game unmutes it.
  4. The admin portal edits prompt/model/thresholds/interval live.
  5. Which implementation fills each role is chosen from one config file.

WORKING STYLE: this is a well-designed open-source system meant for third-party
implementations of any role — favor clean contracts over shortcuts. Ask clarifying
questions before large structural moves, and validate each contract with a running
slice rather than speccing in a vacuum. The laptop host and LAN IP may have changed
since earlier notes — detect them, don't hardcode.
```

# AdalogHole — architecture

**Audience:** future Claude contexts and human contributors. This is the canonical
"what components exist and how they connect" document. Read it before working on
any part of the system. It is an **architecture design**, not a formal/frozen
spec — the boundaries here are meant to be stable; the internals behind them are
free to change as we learn.

---

## 1. What AdalogHole is

An open-source device that **watches a TV with a camera and mutes the
commercials** during live sports (baseball first, other sports next), then
unmutes when the game returns. The name = **Ad**vertisement + the **Analog
Hole**: it reads the screen *optically*, so it needs no HDMI, no app, no account,
and no permission from the TV — and works on any TV ever made.

The core loop is always the same: **look → decide → act.**

---

## 2. Design principles

1. **Roles are contracts.** The system is a small set of roles (Sensor,
   Classifier, Brain, Actuator, Controller). Each role is defined by a contract —
   the data it accepts and produces — not by a particular implementation. Think
   "abstract class + concrete implementations, chosen at startup."
2. **One contract, two bindings.** Every seam between roles has:
   - an **in-process binding** (a normal function/method call) used when the two
     roles share a process, and
   - a **wire binding** (HTTP + JSON) used when the roles live on different
     devices.
   The fields are identical either way. **Migrating a role to another device =
   flipping that one seam from the in-process binding to the wire binding. The
   contract does not change.** This is the whole point of the architecture.
3. **Freeze the seams, keep the guts soft.** The contracts between roles should
   be stable. What happens *inside* a role — the classifier prompt, the model,
   the debounce tuning — is expected to churn and must not leak across a seam.
4. **Cheap and easy to run.** The minimum viable deployment is a **Sensor** plus
   a laptop/server on the same Wi-Fi. No cloud account required beyond whatever
   the chosen Classifier needs (e.g. an LLM key), and that stays optional/
   swappable.
5. **Open and pluggable.** Anyone should be able to supply *any one role* — a
   phone as the Brain, an NVIDIA/Jetson box running a local model as the
   Classifier, a custom Actuator — and have it interoperate. So role contracts
   must be implementation-agnostic (no provider-specific concepts in the shared
   contract).

---

## 3. The five roles

| Role | Responsibility | Contract (the "abstract method") |
| --- | --- | --- |
| **Sensor** | Grab a frame (and optionally an audio level) on a cadence and submit it to the Brain. | `→ Frame` |
| **Classifier** | Turn a frame (+ optional context) into a verdict. *Pluggable inference.* | `classify(Frame, Context) → Verdict` |
| **Brain** | The hub. Runs the decision state machine, owns authoritative state + settings, calls the Classifier, emits Commands, serves Status, accepts Control. | see §4–§6 |
| **Actuator** | Execute a command — IR mute/unmute, soundbar source-switch. Owns the learned IR code catalog. Declares its capabilities. | `execute(Command) → Ack` |
| **Controller / UI** | Human in/out: override knob, status display, admin/settings portal. | sends `Control`, reads `Status`, edits `Settings` |

Notes:

- **Decision logic lives *inside* the Brain**, not as its own role — you don't
  swap it independently. The **Classifier is the one internal seam we formalize**,
  because swapping inference (hosted LLM ↔ local model) is an explicit goal.
- **Roles are logical, not physical.** One process may fulfill several roles
  (e.g. a phone app = Sensor + Brain + Controller). The contracts must read
  cleanly even then — which is exactly why the in-process binding exists.

### Per-role detail

**Sensor** — Produces `Frame`s. The Sensor owns the **cadence** (how often to
sample), because in the final hardware the sensor device is what runs the timer.
Reference impl: Python + OpenCV webcam. Others: Raspberry Pi camera, ESP32-S3
camera, phone camera.

**Classifier** — Pure inference: `Frame (+Context) → Verdict`. It knows nothing
about IR, muting, or debounce. Its own configuration (prompt, model id, API key,
model weights) is **private to the implementation** and never appears in the
shared contract — a local model has no "prompt," a hosted LLM has no "weights
path." Reference impl: a hosted **Claude** vision model using **structured
output** (`output_config.format` json_schema — a typed verdict, not tool
calling). *(For model ids / pricing, consult the `claude-api` skill and the
existing repo notes — do not hardcode guesses here.)* Others: a Jetson/GPU box
running an open VLM, an on-phone model, a classical-CV detector.

**Brain** — The coordinator and the only stateful hub. It: receives frames, calls
the Classifier, feeds verdicts through the **decision state machine** (§6), holds
the authoritative A/V state and the **generic** settings, emits `Command`s, and
exposes `Status`/`Control` to the Controller. There is one Brain per TV.

**Actuator** — Consumes `Command`s and drives IR. Owns the **IR code catalog**
(learned codes as portable data). **Declares capabilities** so the Brain adapts:
e.g. `can_mute`, `can_switch_source`, list of known targets. Reference impl:
USB-UIRT via LIRC on the laptop. Others: Raspberry Pi GPIO (IR LED + TSOP
receiver), ESP32 IR, a networked IR blaster.

**Controller / UI** — Everything human-facing: the **override knob** (force
mute/unmute, lock, return to auto), the **status display** ("you always know what
it's thinking"), and the **admin portal** for editing `Settings`. Reference impl:
the web admin portal; later a physical rotary encoder + LCD, or a phone UI.

---

## 4. Data contracts

Reference shapes (JSON on the wire; the in-process binding passes the same fields
as objects). These are the design intent, not a frozen schema.

```jsonc
// Frame  (Sensor → Brain)   — the JPEG bytes travel as the HTTP body;
//                             this metadata travels as headers or a small JSON sidecar.
{ "source_id": "laptop-webcam-0", "ts": 1730000000.0, "seq": 42,
  "width": 1600, "height": 1200, "audio_level": 0.0 /* optional */ }

// Context  (Brain → Classifier)  — optional hints to sharpen classification
{ "program": "baseball game", "sport": "baseball" /* optional, extensible */ }

// Verdict  (Classifier → Brain)
{ "label": "content" | "commercial" | "unknown",
  "confidence": 0.0,            // 0..1
  "reason": "short human-readable explanation" }

// Command  (Brain → Actuator)
{ "op": "mute" | "unmute" | "source_switch" | "noop",
  "target": "tv" | "soundbar",
  "code_ref": "tv.mute",        // key into the Actuator's IR code catalog
  "reason": "why", "ts": 1730000000.0 }

// Ack  (Actuator → Brain)
{ "ok": true, "executed": true, "detail": "" }

// Capabilities  (Actuator → Brain)
{ "can_mute": true, "can_switch_source": false, "targets": ["tv"] }

// Control  (Controller → Brain)
{ "override": "auto" | "force_mute" | "force_unmute",
  "lock": false }

// Status  (Brain → Controller)  — what the LCD/UI renders
{ "mode": "auto" | "override" | "locked",
  "av_state": "unmuted" | "muted" | "music",
  "last_label": "content", "last_confidence": 0.87,
  "last_reason": "...", "source_id": "laptop-webcam-0",
  "uptime_s": 1234 }

// Settings  (Controller ↔ Brain)  — GENERIC brain config only.
// Classifier-implementation config (prompt/model/key) is separate and private
// to the chosen Classifier implementation.
{ "sample_interval_s": 3, "flip_threshold": 2,
  "program": "baseball game", "soundbar_music_enabled": false }
```

---

## 5. How the roles connect

```
 Sensor ──Frame──▶ Brain ──Frame+Context──▶ Classifier
                    │  ◀────────Verdict──────┘
                    │
                    ├──Command──▶ Actuator ──▶ IR to TV / soundbar
                    │  ◀──Ack────┘
                    │
   Controller ──Control──▶ │
   Controller ◀──Status──── │
   Admin UI  ◀──Settings──▶ ┘
```

**Where the Command goes** — two delivery styles, *same `Command` contract*:

- **Standalone Actuator:** the Brain pushes the `Command` to the Actuator seam.
- **Sensor+Actuator on one device** (e.g. an ESP32 that both captures and fires
  IR): the `Command` may ride back as the **response to the frame submission**,
  so the device acts on the reply without a second channel. This is exactly what
  the original firmware `/classify` response did — preserved and generalized.

---

## 6. Decision state machine (inside the Brain)

Turns a stream of `Verdict`s into stable A/V actions. This is the tunable core;
its knobs live in `Settings`.

- **Labels:** `content` (keep the sound — the game), `commercial` (mute),
  `unknown` (ambiguous frame).
- **Debounce / hysteresis:** flip the A/V state only after **`flip_threshold`**
  consecutive same-label frames. `unknown` **holds** the current state. This
  prevents flapping on a single misread frame.
- **`mode`** (who is in charge):
  - `auto` — the classifier drives.
  - `override` — the user forced a state via the knob; classifier suggestions are
    ignored until released back to `auto`.
  - `locked` — hold the current state, ignore the classifier (e.g. "leave it
    alone").
- **`av_state`** (what is currently commanded): `unmuted` → `muted` →
  (optionally) `music` (soundbar switched to a music source during the break),
  and back.
- **Transitions emit `Command`s** on change only (mute / unmute / source_switch),
  never every frame.

---

## 7. Config-driven wiring (the "simple script")

Which implementation fills each role is chosen **at startup** from one small
config file — the abstract-class/factory pattern:

```toml
# adaloghole.toml  (illustrative)
[roles]
sensor     = "webcam"     # webcam | picamera | esp32(remote) ...
classifier = "claude"     # claude | local-vlm | ...
brain      = "local"
actuator   = "lirc"       # lirc | pigpio | esp32(remote) | none
controller = "admin-web"

[transport]
# in-process by default; a role marked remote uses the HTTP binding
sensor   = "in-process"
actuator = "in-process"

[sensor.webcam]
device = 0
sample_interval_s = 3

[classifier.claude]
# implementation-private config (NOT part of any shared contract)
model = "..."             # see the claude-api skill for current model ids
# api_key lives in a gitignored secrets store, never in this file
```

In code: a `Protocol`/ABC per role, a registry mapping the config string to a
concrete class, and a bootstrap that instantiates the selected implementations
and wires their bindings. Adding a new implementation = write a class + register
it; no other role changes.

---

## 8. Reference transport (HTTP + JSON)

The normative wire binding when a seam crosses devices. Contracts stay
transport-agnostic, so MQTT/websocket/etc. can be added later without changing
the data shapes.

| Seam | Method | Endpoint | Body → Response |
| --- | --- | --- | --- |
| Sensor → Brain | POST | `/frame` | JPEG body (+ meta) → `{verdict, status, command?}` |
| Brain → Actuator | POST | `/command` | `Command` → `Ack` |
| Brain ← Actuator | GET | `/capabilities` | → `Capabilities` |
| Controller → Brain | POST | `/control` | `Control` → `Status` |
| Controller ← Brain | GET | `/status` | → `Status` |
| Controller ↔ Brain | GET/PUT | `/settings` + `/admin` | `Settings` (portal is the HTML view) |

> **Relationship to the existing server.** Today `server/` exposes a single
> `POST /classify` that *conflates* frame-intake + classification + decision and
> returns `{label, confidence, reason, action, muted}`. Under this architecture
> that becomes the **Brain's `/frame` seam**, with the classification factored
> out behind the **Classifier** contract and the generic vs. classifier-private
> config separated. Step 1 (§9) does that refactor while keeping the loop working.

---

## 9. Build roadmap & current state

The strategy is **laptop-first, hardware-last** — develop where iteration is
instant, then re-host roles onto constrained devices. Each phase is the *same
five roles*; only where they run (and which seams cross a wire) changes.

| Role | ① Laptop | ② Raspberry Pi | ③ ESP32 sensor | ④ Phone brain (later) |
| --- | --- | --- | --- | --- |
| Sensor | webcam (Python) | Pi cam / webcam | **ESP32** *(→ wire)* | phone camera |
| Classifier | Claude (hosted) | Claude / local | on Pi/server | on-phone / hosted |
| Brain | laptop | Pi | Pi/server | **phone** |
| Actuator | USB-UIRT / LIRC | Pi GPIO | Pi *or* ESP32 | networked blaster |
| Controller | admin portal | portal + knob | knob + LCD *(→ wire)* | phone UI |
| **Seams on the wire** | Sensor↔Brain (localhost) | none (one box) | Sensor↔Brain, maybe Controller↔Brain | Actuator (external) |

- **Phase ① (now):** all five roles in one Python deployment on the laptop.
  Sensor = USB webcam pointed at the TV. Classifier = hosted Claude. Actuator =
  **USB-UIRT over LIRC** (learn TV mute — and later soundbar — codes with
  `irrecord`, fire with `irsend`). Full closed loop: see an ad → mute the real
  TV, with clean autoexposed webcam frames. **Recommendation:** run the
  Sensor↔Brain seam over localhost HTTP even in Phase 1, since it's the first
  seam to go remote (Phase ③) — exercising it early keeps the contract honest.
- **Phase ②:** re-host the same roles onto a Raspberry Pi (the "one cheap box on
  your Wi-Fi" target). IR moves to Pi GPIO with the on-hand emitter/receiver, or
  the USB-UIRT just plugs into the Pi. Add the soundbar source-switch and
  always-on robustness.
- **Phase ③:** the **ESP32 becomes the Sensor** (dumb JPEG poster) — which is the
  *original* architecture, so the tabled `firmware/` slots in here once the logic
  is proven. Enclosure (walnut / aluminum / printed). Re-validate against the
  OV2640's rougher frames (a *late* de-risk).
- **Phase ④ (later):** a phone as Sensor + Brain + Controller; needs an external
  networked Actuator. This is why the Brain's outward contract must stay clean.

### What exists in the repo today

- `server/` — the current Brain-ish server (FastAPI): `classifier.py`,
  `decision.py`, `settings.py`, `routes_device.py` (`/classify`),
  `routes_admin.py` (admin portal), `tools/classify_cli.py`. **Reused** in Phase
  1, refactored into the role structure above.
- `firmware/` — the ESP32-S3 capture→POST→IR skeleton (compiles; end-to-end loop
  was demonstrated). **Tabled to Phase ③** — not thrown away, deferred.
- `docs/hardware-prototype.md`, `docs/stage1-core-loop-plan.md`,
  `docs/stage1-handoff-next-session.md` — the **ESP32-first plan, now
  superseded** by this document (they carry banners saying so). Useful history
  for Phase ③.

### Where a fresh context starts

Phase 1: factor `server/` into the five roles behind interfaces (config-selected
per §7), add the Python **webcam Sensor** and the **LIRC Actuator**, keep the
existing admin portal as the Controller, and close the loop end-to-end on the
laptop. Preserve the `/frame` (née `/classify`) contract so the ESP32 can rejoin
unchanged in Phase 3.

There is a ready-to-use, copy-paste kickoff prompt for a fresh context in
[`phase1-kickoff.md`](./phase1-kickoff.md).

---

## 10. Non-goals / open questions (for now)

- **Single TV, single Brain, local network.** No multi-unit coordination, no
  cloud sync, no mobile app *yet* — but the contracts intentionally leave room
  (the Brain's outward contract is what a phone brain would implement).
- **Capability negotiation** is declared (Actuator `Capabilities`) but wiring is
  static config for now — components are told where their peers are; they don't
  discover each other dynamically.
- **A formal conformance spec + test harness** (RFC-style MUST/SHOULD, versioned,
  with a suite that validates third-party implementations) is deliberately
  deferred until Phase 1 proves these shapes. This doc is the design; the spec is
  a later promotion of it.

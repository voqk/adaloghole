"""Debounce core behavior — the safety net for the Phase 1 refactor.

Written against the original app.decision.DecisionEngine; the class moves to
app.roles.brain.debounce during the refactor with logic unchanged, so these
tests must stay green throughout.
"""

import pytest

try:
    from app.roles.brain.debounce import DecisionEngine
except ImportError:  # pre-refactor location
    from app.decision import DecisionEngine


def feed_all(engine, labels):
    return [engine.feed(label) for label in labels]


def test_flip_requires_threshold_consecutive_frames():
    e = DecisionEngine(flip_threshold=2)
    assert e.feed("commercial") == {"action": "none", "muted": False}
    assert e.feed("commercial") == {"action": "mute", "muted": True}


def test_single_frame_never_flips():
    e = DecisionEngine(flip_threshold=2)
    e.feed("commercial")
    assert e.muted is False


def test_unknown_holds_state_and_does_not_reset_pending():
    e = DecisionEngine(flip_threshold=3)
    e.feed("commercial")
    assert e.feed("unknown") == {"action": "none", "muted": False}
    # unknown is a no-op: the pending count is preserved, not reset
    e.feed("commercial")
    assert e.feed("commercial") == {"action": "mute", "muted": True}


def test_contrary_label_resets_pending_count():
    e = DecisionEngine(flip_threshold=2)
    e.feed("commercial")
    e.feed("program")  # contrary while unmuted -> already-desired, clears pending
    e.feed("commercial")
    assert e.muted is False  # count restarted; one frame is not enough
    e.feed("commercial")
    assert e.muted is True


def test_unmute_path_symmetric():
    e = DecisionEngine(flip_threshold=2)
    feed_all(e, ["commercial", "commercial"])  # -> muted
    assert e.muted is True
    assert e.feed("program") == {"action": "none", "muted": True}
    assert e.feed("program") == {"action": "unmute", "muted": False}


def test_already_in_desired_state_is_noop():
    e = DecisionEngine(flip_threshold=2)
    for _ in range(5):
        assert e.feed("program") == {"action": "none", "muted": False}


def test_threshold_one_flips_immediately():
    e = DecisionEngine(flip_threshold=1)
    assert e.feed("commercial")["action"] == "mute"
    assert e.feed("program")["action"] == "unmute"


@pytest.mark.parametrize("labels,expected_muted", [
    (["commercial", "unknown", "commercial"], True),   # unknown doesn't break a run
    (["commercial", "program", "commercial"], False),  # contrary resets
])
def test_sequences(labels, expected_muted):
    e = DecisionEngine(flip_threshold=2)
    feed_all(e, labels)
    assert e.muted is expected_muted

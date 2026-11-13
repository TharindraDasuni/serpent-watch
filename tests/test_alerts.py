from serpentwatch.alerts import AlertGate


def test_needs_consecutive_hits():
    gate = AlertGate(confirm_frames=3, cooldown_seconds=0)
    assert gate.update(True, 0) is False
    assert gate.update(True, 1) is False
    assert gate.update(True, 2) is True


def test_gap_resets_streak():
    gate = AlertGate(confirm_frames=2, cooldown_seconds=0)
    gate.update(True, 0)
    gate.update(False, 1)
    assert gate.update(True, 2) is False
    assert gate.update(True, 3) is True


def test_cooldown_suppresses_repeat_alerts():
    gate = AlertGate(confirm_frames=1, cooldown_seconds=60)
    assert gate.update(True, 100) is True
    assert gate.update(True, 130) is False
    assert gate.update(True, 161) is True

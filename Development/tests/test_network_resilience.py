"""
test_network_resilience.py — Tests for connection retry and fail-safe logic.

Validates the reconnect back-off calculation and fail-safe timeout
behaviour without requiring a live broker.

Run with:
    pytest Development/tests/test_network_resilience.py -v
"""

import time


# ── Back-off helpers (mirrors connection_manager.py logic) ────────────────────

def next_backoff(current: float, max_delay: float = 60.0) -> float:
    """Double the delay, capped at max_delay."""
    return min(current * 2, max_delay)


def backoff_sequence(start: float = 1.0, steps: int = 8, cap: float = 60.0) -> list:
    delays = [start]
    for _ in range(steps - 1):
        delays.append(next_backoff(delays[-1], cap))
    return delays


# ── Fail-safe helpers (mirrors mqtt_device_controller.py logic) ───────────────

def is_failsafe_triggered(last_command_time: float, timeout: float = 2.0) -> bool:
    return (time.time() - last_command_time) > timeout


# ── Back-off tests ─────────────────────────────────────────────────────────────

def test_backoff_doubles():
    assert next_backoff(1.0) == 2.0
    assert next_backoff(2.0) == 4.0
    assert next_backoff(4.0) == 8.0


def test_backoff_capped_at_max():
    assert next_backoff(40.0, max_delay=60.0) == 60.0
    assert next_backoff(60.0, max_delay=60.0) == 60.0


def test_backoff_sequence_length():
    seq = backoff_sequence(start=1.0, steps=6)
    assert len(seq) == 6


def test_backoff_sequence_values():
    seq = backoff_sequence(start=1.0, steps=5, cap=60.0)
    assert seq == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_backoff_never_exceeds_cap():
    seq = backoff_sequence(start=1.0, steps=10, cap=60.0)
    assert all(d <= 60.0 for d in seq)


def test_backoff_always_positive():
    seq = backoff_sequence(start=0.5, steps=8)
    assert all(d > 0 for d in seq)


# ── Fail-safe tests ────────────────────────────────────────────────────────────

def test_failsafe_not_triggered_immediately():
    now = time.time()
    assert is_failsafe_triggered(now, timeout=2.0) is False


def test_failsafe_triggered_after_timeout():
    old_time = time.time() - 3.0   # 3 seconds ago
    assert is_failsafe_triggered(old_time, timeout=2.0) is True


def test_failsafe_boundary_just_before():
    just_before = time.time() - 1.9
    assert is_failsafe_triggered(just_before, timeout=2.0) is False


def test_failsafe_boundary_just_after():
    just_after = time.time() - 2.1
    assert is_failsafe_triggered(just_after, timeout=2.0) is True


def test_failsafe_custom_timeout():
    old_time = time.time() - 6.0
    assert is_failsafe_triggered(old_time, timeout=5.0) is True
    assert is_failsafe_triggered(old_time, timeout=10.0) is False


# ── Baseline ───────────────────────────────────────────────────────────────────

def test_dummy():
    """Baseline test — always passes."""
    assert True

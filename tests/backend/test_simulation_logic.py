"""Unit tests for the simulation engine's pure logic (no database needed)."""

import random

from app.services.simulation import (
    EV_STATES,
    PARKING_ORDER,
    SPEED_FACTOR,
    TRAFFIC_ORDER,
    _step,
)


def test_step_never_leaves_bounds():
    rng = random.Random(42)
    state = "low"
    for _ in range(500):
        state = _step(state, TRAFFIC_ORDER, rng)
        assert state in TRAFFIC_ORDER
    state = "full"
    for _ in range(500):
        state = _step(state, PARKING_ORDER, rng)
        assert state in PARKING_ORDER


def test_step_moves_at_most_one_state():
    rng = random.Random(7)
    for start in TRAFFIC_ORDER:
        for _ in range(100):
            new = _step(start, TRAFFIC_ORDER, rng)
            assert abs(TRAFFIC_ORDER.index(new) - TRAFFIC_ORDER.index(start)) <= 1


def test_speed_factor_monotonically_decreases_with_congestion():
    factors = [SPEED_FACTOR[s] for s in TRAFFIC_ORDER]
    assert factors == sorted(factors, reverse=True)
    assert all(0 < f <= 1 for f in factors)


def test_ev_states_complete():
    assert set(EV_STATES) == {"available", "busy", "offline"}

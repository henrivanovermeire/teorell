"""Tests for LiveSession real-time stepper."""

from __future__ import annotations

import pytest

from teorell_core import LiveSession, Patient, Sex


def _session() -> LiveSession:
    return LiveSession(Patient(age=40, weight=70, height=170, sex=Sex.MALE))


def test_step_advances_time() -> None:
    s = _session()
    s.step(0.1)
    assert s.t_min == pytest.approx(0.1)
    assert len(s.history) >= 2


def test_propofol_bolus_raises_cp() -> None:
    s = _session()
    before = s.snapshot().propofol_cp
    s.bolus_propofol(100.0)
    after = s.snapshot()
    assert after.propofol_cp > before
    assert after.propofol_cp == pytest.approx(100.0 / 4.27, rel=0.01)


def test_infusion_and_volatile_change_bis() -> None:
    s = _session()
    s.set_propofol_infusion(6.0)
    s.set_vaporizer(3.0, 6.0)
    for _ in range(50):
        s.step(0.1)
    assert s.snapshot().bis < 90.0
    assert s.snapshot().vrg > 0.0


def test_remi_bolus_increases_opioid_eq() -> None:
    s = _session()
    s.bolus_remifentanil(50.0)
    # Effect-site lags plasma; advance until Ce (and remi-eq) rise.
    for _ in range(20):
        s.step(0.1)
    assert s.snapshot().opioid_remi_eq > 0.0
    assert s.snapshot().remifentanil_ce > 0.0

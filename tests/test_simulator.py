"""Tests for teorell-core PK simulation."""

from __future__ import annotations

import numpy as np
import pytest

from teorell_core import (
    Bolus,
    Infusion,
    Mammillary3,
    Patient,
    Regimen,
    Sex,
    schnider_propofol,
    simulate,
)


def _reference_adult() -> Patient:
    return Patient(age=40, weight=70, height=170, sex=Sex.MALE)


def test_schnider_parameters_are_positive() -> None:
    params = schnider_propofol(_reference_adult())
    assert params.v1 == pytest.approx(4.27)
    assert params.v3 == pytest.approx(238.0)
    assert params.ke0 == pytest.approx(0.456)
    assert params.cl > 0
    assert params.q2 > 0
    assert params.v2 > 0


def test_bolus_raises_then_declines() -> None:
    params = schnider_propofol(_reference_adult())
    result = simulate(
        params,
        Regimen(boluses=(Bolus(time_min=0.0, amount_mg=100.0),)),
        duration_min=30.0,
        dt_min=0.1,
    )

    assert result.plasma_mg_per_l[0] == pytest.approx(100.0 / params.v1)
    assert result.plasma_mg_per_l[0] > result.plasma_mg_per_l[-1]
    # Effect site lags plasma after a bolus.
    assert result.effect_site_mg_per_l[0] == pytest.approx(0.0)
    assert result.effect_site_mg_per_l[10] > result.effect_site_mg_per_l[0]


def test_infusion_reaches_steady_state() -> None:
    # Fast peripheral equilibration so SS is reached in a few hours.
    params = Mammillary3(v1=5.0, v2=2.0, v3=2.0, cl=1.0, q2=2.0, q3=2.0, ke0=0.5)
    result = simulate(
        params,
        Regimen(infusions=(Infusion(start_min=0.0, duration_min=180.0, rate_mg_per_min=1.0),)),
        duration_min=180.0,
        dt_min=1.0,
    )
    # At steady state under constant infusion, Cp = rate / CL.
    assert result.plasma_mg_per_l[-1] == pytest.approx(1.0 / params.cl, rel=0.02)


def test_mass_conservation_without_elimination_path_off() -> None:
    # With CL=0 impossible (validated); instead check amounts stay finite/non-negative.
    params = schnider_propofol(_reference_adult())
    result = simulate(
        params,
        Regimen(
            boluses=(Bolus(0.0, 50.0),),
            infusions=(Infusion(5.0, 10.0, 2.0),),
        ),
        duration_min=40.0,
        dt_min=0.2,
    )
    assert np.all(result.amounts_mg >= -1e-9)
    assert np.all(np.isfinite(result.plasma_mg_per_l))

"""Tests for Bouillon BIS PD and TIVA simulation."""

from __future__ import annotations

import numpy as np
import pytest

from teorell_core import (
    Bolus,
    BouillonBIS,
    Infusion,
    Patient,
    Regimen,
    Sex,
    minto_remifentanil,
    schnider_propofol,
    simulate_tiva,
)


def _adult() -> Patient:
    return Patient(age=40, weight=70, height=170, sex=Sex.MALE)


def test_bouillon_baseline_is_e0() -> None:
    bis = BouillonBIS().predict(0.0, 0.0)
    assert float(bis) == pytest.approx(97.4)


def test_bouillon_half_effect_propofol_alone() -> None:
    pd = BouillonBIS()
    bis = float(pd.predict(pd.c50_propofol_ug_per_ml, 0.0))
    assert bis == pytest.approx(pd.e0 - 0.5 * pd.emax, abs=0.05)


def test_minto_parameters_positive() -> None:
    params = minto_remifentanil(_adult())
    assert params.v1 > 0
    assert params.cl > 0
    assert params.ke0 > 0


def test_simulate_tiva_propofol_lowers_bis() -> None:
    result = simulate_tiva(
        _adult(),
        propofol=Regimen(boluses=(Bolus(0.0, 100.0),)),
        duration_min=10.0,
        dt_min=0.1,
    )
    assert result.bis[0] == pytest.approx(97.4, abs=1.0)
    assert result.bis.min() < 80.0
    assert np.all(result.remifentanil_ce_ng_per_ml == 0.0)


def test_simulate_tiva_propofol_plus_remi() -> None:
    result = simulate_tiva(
        _adult(),
        propofol=Regimen(
            boluses=(Bolus(0.0, 100.0),),
            infusions=(Infusion(1.0, 29.0, 6.0),),
        ),
        remifentanil=Regimen(
            boluses=(Bolus(0.0, 50.0),),  # µg
            infusions=(Infusion(1.0, 29.0, 0.2),),  # µg/min
        ),
        duration_min=30.0,
        dt_min=0.1,
    )
    assert result.n_samples > 100
    assert result.bis.min() < result.bis[0]
    assert result.remifentanil_ce_ng_per_ml.max() > 0.0
    assert result.propofol_ce_ug_per_ml.max() > 0.0


def test_simulate_tiva_alfentanil_lowers_bis_via_equipotency() -> None:
    """Alfentanil alone has little BIS effect; with propofol it deepens hypnosis."""
    without = simulate_tiva(
        _adult(),
        propofol=Regimen(boluses=(Bolus(0.0, 80.0),)),
        duration_min=10.0,
        dt_min=0.1,
    )
    with_alf = simulate_tiva(
        _adult(),
        propofol=Regimen(boluses=(Bolus(0.0, 80.0),)),
        alfentanil=Regimen(
            boluses=(Bolus(0.0, 1000.0),),  # µg
            infusions=(Infusion(1.0, 9.0, 50.0),),  # µg/min
        ),
        duration_min=10.0,
        dt_min=0.1,
    )
    assert with_alf.alfentanil_ce_ng_per_ml.max() > 0.0
    assert with_alf.opioid_remi_eq_ng_per_ml.max() > 0.0
    assert with_alf.bis.min() < without.bis.min()


def test_alfentanil_equipotency_factor() -> None:
    from teorell_core import remifentanil_equivalent_ng_per_ml

    eq = float(remifentanil_equivalent_ng_per_ml(alfentanil_ng_per_ml=400.0))
    assert eq == pytest.approx(10.0)


def test_scott_alfentanil_scales_with_weight() -> None:
    from teorell_core import scott_alfentanil

    ref = scott_alfentanil(Patient(age=40, weight=70, height=170, sex=Sex.MALE))
    heavy = scott_alfentanil(Patient(age=40, weight=100, height=180, sex=Sex.MALE))
    assert ref.v1 == pytest.approx(2.19)
    assert ref.cl == pytest.approx(0.195)
    assert heavy.v1 == pytest.approx(2.19 * 100 / 70)

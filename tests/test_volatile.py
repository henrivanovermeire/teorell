"""Tests for Gas Man–style volatile PK and Schumacher/Bouillon BIS."""

from __future__ import annotations

import numpy as np
import pytest

from teorell_core import (
    CombinedBIS,
    Patient,
    SEVOFLURANE,
    SchumacherHypnotic,
    Sex,
    VolatileSchedule,
    simulate_anesthesia,
    simulate_volatile,
)


def test_sevoflurane_vrg_rises_toward_vaporizer() -> None:
    result = simulate_volatile(
        SEVOFLURANE,
        VolatileSchedule(segments=((0.0, 2.0, 8.0),)),
        duration_min=30.0,
        dt_min=0.05,
    )
    assert result.vrg_vol_pct[0] == pytest.approx(0.0)
    assert result.vrg_vol_pct[-1] > 0.5
    assert result.fa_vol_pct[-1] > result.vrg_vol_pct[-1] * 0.5
    assert result.mac_fraction[-1] == pytest.approx(
        result.vrg_vol_pct[-1] / SEVOFLURANE.mac_vol_pct
    )


def test_higher_fgf_raises_fi_faster() -> None:
    low = simulate_volatile(
        SEVOFLURANE,
        VolatileSchedule(segments=((0.0, 3.0, 1.0),)),
        duration_min=5.0,
        dt_min=0.05,
    )
    high = simulate_volatile(
        SEVOFLURANE,
        VolatileSchedule(segments=((0.0, 3.0, 10.0),)),
        duration_min=5.0,
        dt_min=0.05,
    )
    assert high.fi_vol_pct[20] > low.fi_vol_pct[20]


def test_schumacher_sevo_c50_halves_bis() -> None:
    pd = CombinedBIS()
    bis = float(pd.predict(sevoflurane_eq_vol_pct=1.53))
    assert bis == pytest.approx(97.4 - 0.5 * 97.4, abs=0.1)


def test_schumacher_propofol_additive_with_sevo() -> None:
    u = SchumacherHypnotic().hypnotic_u(3.68, 1.53)
    assert float(u) == pytest.approx(2.0)


def test_simulate_anesthesia_sevo_only_lowers_bis() -> None:
    result = simulate_anesthesia(
        volatile_schedule=VolatileSchedule(segments=((0.0, 3.0, 6.0),)),
        duration_min=20.0,
        dt_min=0.1,
    )
    assert result.bis[0] == pytest.approx(97.4, abs=0.5)
    assert result.bis.min() < 80.0
    assert result.vrg_vol_pct.max() > 0.0
    assert np.all(result.propofol_ce_ug_per_ml == 0.0)


def test_simulate_anesthesia_requires_patient_for_iv() -> None:
    from teorell_core import Bolus, Regimen

    with pytest.raises(ValueError, match="patient"):
        simulate_anesthesia(
            propofol=Regimen(boluses=(Bolus(0.0, 50.0),)),
            duration_min=5.0,
        )


def test_sevo_plus_propofol_deeper_than_sevo_alone() -> None:
    from teorell_core import Bolus, Infusion, Regimen

    patient = Patient(age=40, weight=70, height=170, sex=Sex.MALE)
    sevo = VolatileSchedule(segments=((0.0, 2.0, 6.0),))
    alone = simulate_anesthesia(
        volatile_schedule=sevo,
        duration_min=15.0,
        dt_min=0.1,
    )
    combo = simulate_anesthesia(
        patient,
        propofol=Regimen(
            boluses=(Bolus(0.0, 80.0),),
            infusions=(Infusion(1.0, 14.0, 4.0),),
        ),
        volatile_schedule=sevo,
        duration_min=15.0,
        dt_min=0.1,
    )
    assert combo.bis.min() < alone.bis.min()

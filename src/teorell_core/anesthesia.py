"""Combined IV + volatile anesthesia simulation (BAS-style dual core)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from teorell_core.dosing import Regimen
from teorell_core.patient import Patient
from teorell_core.pd import CombinedBIS
from teorell_core.tiva import TivaResult, simulate_tiva
from teorell_core.volatile.gasman import (
    BodyPhysiology,
    VolatileResult,
    VolatileSchedule,
    simulate_volatile,
)
from teorell_core.volatile.properties import SEVOFLURANE, VolatileAgent


@dataclass(frozen=True, slots=True)
class AnesthesiaResult:
    """Dual-core trajectories with predicted BIS and MAC."""

    time_min: NDArray[np.float64]
    propofol_ce_ug_per_ml: NDArray[np.float64]
    opioid_remi_eq_ng_per_ml: NDArray[np.float64]
    sevoflurane_eq_vol_pct: NDArray[np.float64]
    fi_vol_pct: NDArray[np.float64]
    fa_vol_pct: NDArray[np.float64]
    vrg_vol_pct: NDArray[np.float64]
    mac_fraction: NDArray[np.float64]
    bis: NDArray[np.float64]
    tiva: TivaResult | None
    volatile: VolatileResult | None

    @property
    def n_samples(self) -> int:
        return int(self.time_min.size)


def simulate_anesthesia(
    patient: Patient | None = None,
    *,
    propofol: Regimen | None = None,
    remifentanil: Regimen | None = None,
    alfentanil: Regimen | None = None,
    volatile_agent: VolatileAgent = SEVOFLURANE,
    volatile_schedule: VolatileSchedule | None = None,
    duration_min: float,
    dt_min: float = 0.1,
    body: BodyPhysiology | None = None,
    bis_model: CombinedBIS | None = None,
) -> AnesthesiaResult:
    """Run IV and/or volatile cores and predict BIS (Schumacher + Bouillon).

    Volatile VRG tension is MAC-scaled to sevoflurane-equivalent vol% for the
    Schumacher hypnotic arm. Opioids use existing remifentanil equipotency.
    """
    if (
        propofol is None
        and remifentanil is None
        and alfentanil is None
        and volatile_schedule is None
    ):
        raise ValueError("provide at least one IV regimen or a volatile schedule")
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")

    pd = bis_model if bis_model is not None else CombinedBIS()
    has_iv = any(x is not None for x in (propofol, remifentanil, alfentanil))
    if has_iv and patient is None:
        raise ValueError("patient is required when simulating IV drugs")

    tiva: TivaResult | None = None
    vol: VolatileResult | None = None

    if has_iv:
        assert patient is not None
        tiva = simulate_tiva(
            patient,
            propofol=propofol,
            remifentanil=remifentanil,
            alfentanil=alfentanil,
            duration_min=duration_min,
            dt_min=dt_min,
        )

    if volatile_schedule is not None:
        vol = simulate_volatile(
            volatile_agent,
            volatile_schedule,
            duration_min=duration_min,
            dt_min=min(dt_min, 0.05),
            body=body,
        )

    times = _merge_times(
        None if tiva is None else tiva.time_min,
        None if vol is None else vol.time_min,
        duration_min,
        dt_min,
    )

    if tiva is not None:
        prop_ce = np.interp(times, tiva.time_min, tiva.propofol_ce_ug_per_ml)
        opioid = np.interp(times, tiva.time_min, tiva.opioid_remi_eq_ng_per_ml)
    else:
        prop_ce = np.zeros_like(times)
        opioid = np.zeros_like(times)

    if vol is not None:
        fi = np.interp(times, vol.time_min, vol.fi_vol_pct)
        fa = np.interp(times, vol.time_min, vol.fa_vol_pct)
        vrg = np.interp(times, vol.time_min, vol.vrg_vol_pct)
        mac = np.interp(times, vol.time_min, vol.mac_fraction)
        # Convert VRG tension to sevoflurane-equivalent vol% for Schumacher C50_sevo.
        if volatile_agent.c50_bis_vol_pct is not None:
            sevo_eq = vrg * (
                float(SEVOFLURANE.c50_bis_vol_pct) / float(volatile_agent.c50_bis_vol_pct)
            )
        else:
            sevo_eq = vrg * (SEVOFLURANE.mac_vol_pct / volatile_agent.mac_vol_pct)
    else:
        fi = fa = vrg = mac = sevo_eq = np.zeros_like(times)

    bis = pd.predict(
        ce_propofol_ug_per_ml=prop_ce,
        sevoflurane_eq_vol_pct=sevo_eq,
        ce_opioid_remi_eq_ng_per_ml=opioid,
    )
    return AnesthesiaResult(
        time_min=times,
        propofol_ce_ug_per_ml=prop_ce,
        opioid_remi_eq_ng_per_ml=opioid,
        sevoflurane_eq_vol_pct=sevo_eq,
        fi_vol_pct=fi,
        fa_vol_pct=fa,
        vrg_vol_pct=vrg,
        mac_fraction=mac,
        bis=bis,
        tiva=tiva,
        volatile=vol,
    )


def _merge_times(
    a: NDArray[np.float64] | None,
    b: NDArray[np.float64] | None,
    duration_min: float,
    dt_min: float,
) -> NDArray[np.float64]:
    regular = np.arange(0.0, duration_min + dt_min * 0.5, dt_min, dtype=np.float64)
    parts = [regular, np.array([0.0, duration_min], dtype=np.float64)]
    if a is not None:
        parts.append(a)
    if b is not None:
        parts.append(b)
    times = np.unique(np.concatenate(parts))
    return times[times <= duration_min + 1e-12]

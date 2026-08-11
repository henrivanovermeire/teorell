"""Combined TIVA simulation with predicted processed-EEG (BIS).

Educational IV path: Schnider propofol + opioid PK (Minto remifentanil,
Scott alfentanil), equipotency conversion, then Bouillon response-surface
PD → predicted BIS. Not for clinical use.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from teorell_core.dosing import Regimen
from teorell_core.models.alfentanil import scott_alfentanil
from teorell_core.models.propofol import schnider_propofol
from teorell_core.models.remifentanil import minto_remifentanil
from teorell_core.patient import Patient
from teorell_core.pd import BouillonBIS, remifentanil_equivalent_ng_per_ml
from teorell_core.simulator import SimulationResult, simulate


@dataclass(frozen=True, slots=True)
class TivaResult:
    """Multi-drug TIVA trajectories with predicted BIS."""

    time_min: NDArray[np.float64]
    propofol_cp_ug_per_ml: NDArray[np.float64]
    propofol_ce_ug_per_ml: NDArray[np.float64]
    remifentanil_cp_ng_per_ml: NDArray[np.float64]
    remifentanil_ce_ng_per_ml: NDArray[np.float64]
    alfentanil_cp_ng_per_ml: NDArray[np.float64]
    alfentanil_ce_ng_per_ml: NDArray[np.float64]
    opioid_remi_eq_ng_per_ml: NDArray[np.float64]
    bis: NDArray[np.float64]
    propofol: SimulationResult | None
    remifentanil: SimulationResult | None
    alfentanil: SimulationResult | None

    @property
    def n_samples(self) -> int:
        return int(self.time_min.size)


def simulate_tiva(
    patient: Patient,
    *,
    propofol: Regimen | None = None,
    remifentanil: Regimen | None = None,
    alfentanil: Regimen | None = None,
    duration_min: float,
    dt_min: float = 0.1,
    bis_model: BouillonBIS | None = None,
) -> TivaResult:
    """Simulate propofol ± remifentanil ± alfentanil and predict BIS.

    Propofol regimen amounts/rates are in mg / mg/min (concentrations µg/mL).
    Remifentanil and alfentanil amounts/rates are in µg / µg/min (ng/mL).
    Alfentanil is converted to remifentanil-equivalent Ce (÷40) for the Bouillon
    surface (equipotency → response-surface PD).
    """
    if propofol is None and remifentanil is None and alfentanil is None:
        raise ValueError("provide at least one drug regimen")
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")

    pd = bis_model if bis_model is not None else BouillonBIS()
    times = _shared_time_grid(
        (propofol, remifentanil, alfentanil),
        duration_min,
        dt_min,
    )

    prop_result, prop_cp, prop_ce = _simulate_drug(
        patient, propofol, schnider_propofol, times, duration_min, dt_min
    )
    remi_result, remi_cp, remi_ce = _simulate_drug(
        patient, remifentanil, minto_remifentanil, times, duration_min, dt_min
    )
    alf_result, alf_cp, alf_ce = _simulate_drug(
        patient, alfentanil, scott_alfentanil, times, duration_min, dt_min
    )

    opioid_eq = remifentanil_equivalent_ng_per_ml(
        remifentanil_ng_per_ml=remi_ce,
        alfentanil_ng_per_ml=alf_ce,
    )
    bis = pd.predict(prop_ce, opioid_eq)
    return TivaResult(
        time_min=times,
        propofol_cp_ug_per_ml=prop_cp,
        propofol_ce_ug_per_ml=prop_ce,
        remifentanil_cp_ng_per_ml=remi_cp,
        remifentanil_ce_ng_per_ml=remi_ce,
        alfentanil_cp_ng_per_ml=alf_cp,
        alfentanil_ce_ng_per_ml=alf_ce,
        opioid_remi_eq_ng_per_ml=opioid_eq,
        bis=bis,
        propofol=prop_result,
        remifentanil=remi_result,
        alfentanil=alf_result,
    )


def _simulate_drug(patient, regimen, param_fn, times, duration_min, dt_min):
    if regimen is None:
        zeros = np.zeros_like(times)
        return None, zeros, zeros
    result = simulate(
        param_fn(patient),
        regimen,
        duration_min=duration_min,
        dt_min=dt_min,
    )
    cp = np.interp(times, result.time_min, result.plasma_mg_per_l)
    ce = np.interp(times, result.time_min, result.effect_site_mg_per_l)
    return result, cp, ce


def _shared_time_grid(
    regimens: tuple[Regimen | None, ...],
    duration_min: float,
    dt_min: float,
) -> NDArray[np.float64]:
    regular = np.arange(0.0, duration_min + dt_min * 0.5, dt_min, dtype=np.float64)
    events: set[float] = {0.0, duration_min}
    for regimen in regimens:
        if regimen is None:
            continue
        for bolus in regimen.boluses:
            if 0.0 <= bolus.time_min <= duration_min:
                events.add(bolus.time_min)
        for infusion in regimen.infusions:
            if 0.0 <= infusion.start_min <= duration_min:
                events.add(infusion.start_min)
            if 0.0 <= infusion.end_min <= duration_min:
                events.add(infusion.end_min)
    times = np.union1d(regular, np.fromiter(events, dtype=np.float64))
    return times[times <= duration_min + 1e-12]

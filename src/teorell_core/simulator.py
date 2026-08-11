"""Time-domain pharmacokinetic simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.linalg import inv, norm
from numpy.typing import NDArray

from teorell_core.dosing import Regimen
from teorell_core.parameters import Mammillary3, MicroRates


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Trajectories from a PK simulation.

    Concentrations are in mg/L (≡ µg/mL).
    """

    time_min: NDArray[np.float64]
    plasma_mg_per_l: NDArray[np.float64]
    effect_site_mg_per_l: NDArray[np.float64]
    amounts_mg: NDArray[np.float64]

    @property
    def n_samples(self) -> int:
        return int(self.time_min.size)


def simulate(
    params: Mammillary3 | MicroRates,
    regimen: Regimen,
    *,
    duration_min: float,
    dt_min: float = 0.1,
) -> SimulationResult:
    """Simulate a 3-compartment (+ effect-site) mammillary model.

    Integration uses the matrix exponential between successive output times.
    Bolus and infusion breakpoints are merged into the time grid so events are
    never skipped when ``dt_min`` does not land on them.
    """
    if duration_min <= 0:
        raise ValueError("duration_min must be positive")
    if dt_min <= 0:
        raise ValueError("dt_min must be positive")

    rates = params.to_micro_rates() if isinstance(params, Mammillary3) else params
    times = _time_grid(regimen, duration_min, dt_min)

    a = rates.system_matrix()
    state = np.zeros(a.shape[0], dtype=np.float64)
    amounts = np.zeros((times.size, a.shape[0]), dtype=np.float64)

    state = _apply_boluses(state, regimen, 0.0)
    amounts[0] = state

    for i in range(1, times.size):
        t_prev = float(times[i - 1])
        t_curr = float(times[i])
        rate = regimen.infusion_rate_at(t_prev)
        state = _advance(state, a, rate, t_curr - t_prev)
        state = _apply_boluses(state, regimen, t_curr)
        amounts[i] = state

    return SimulationResult(
        time_min=times,
        plasma_mg_per_l=amounts[:, 0] / rates.v1,
        effect_site_mg_per_l=amounts[:, 3] / rates.v1,
        amounts_mg=amounts,
    )


def _time_grid(
    regimen: Regimen,
    duration_min: float,
    dt_min: float,
) -> NDArray[np.float64]:
    regular = np.arange(0.0, duration_min + dt_min * 0.5, dt_min, dtype=np.float64)
    events = {0.0, duration_min}
    for bolus in regimen.boluses:
        if 0.0 <= bolus.time_min <= duration_min:
            events.add(bolus.time_min)
    for infusion in regimen.infusions:
        if 0.0 <= infusion.start_min <= duration_min:
            events.add(infusion.start_min)
        end = infusion.end_min
        if 0.0 <= end <= duration_min:
            events.add(end)
    times = np.union1d(regular, np.fromiter(events, dtype=np.float64))
    return times[times <= duration_min + 1e-12]


def _apply_boluses(
    state: NDArray[np.float64],
    regimen: Regimen,
    time_min: float,
) -> NDArray[np.float64]:
    out = state.copy()
    for bolus in regimen.boluses:
        if abs(bolus.time_min - time_min) <= 1e-12:
            out[0] += bolus.amount_mg
    return out


def _advance(
    state: NDArray[np.float64],
    a: NDArray[np.float64],
    infusion_rate_mg_per_min: float,
    dt: float,
) -> NDArray[np.float64]:
    if dt < 0:
        raise ValueError("dt must be non-negative")
    if dt == 0:
        return state.copy()

    phi = _expm(a * dt)
    if infusion_rate_mg_per_min == 0.0:
        return phi @ state

    u = np.array([infusion_rate_mg_per_min, 0.0, 0.0, 0.0], dtype=np.float64)
    x_ss = -inv(a) @ u
    return phi @ (state - x_ss) + x_ss


def _expm(m: NDArray[np.float64]) -> NDArray[np.float64]:
    """Scaling-and-squaring Padé [6/6] matrix exponential."""
    a = np.asarray(m, dtype=np.float64)
    n = a.shape[0]
    ninf = float(norm(a, ord=np.inf))
    s = max(0, int(np.ceil(np.log2(ninf))) + 1) if ninf > 0.0 else 0
    a = a / (2**s)

    eye = np.eye(n, dtype=np.float64)
    a2 = a @ a
    a4 = a2 @ a2
    a6 = a4 @ a2

    b0, b1, b2, b3 = 1.0, 1.0 / 2.0, 1.0 / 10.0, 1.0 / 120.0
    b4, b5, b6 = 1.0 / 1680.0, 1.0 / 30240.0, 1.0 / 665280.0

    u = a @ (b5 * a4 + b3 * a2 + b1 * eye)
    v = b6 * a6 + b4 * a4 + b2 * a2 + b0 * eye
    r = inv(v - u) @ (v + u)
    for _ in range(s):
        r = r @ r
    return r

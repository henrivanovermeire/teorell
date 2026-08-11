"""Gas Man–style uptake and distribution for a single volatile agent.

Educational four-tissue body (VRG / muscle / fat) plus circuit and alveolar
gas, after the classic Eger / Philip Gas Man structure used by Brigham
Anesthesia Simulator for its volatile core.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from teorell_core.volatile.properties import SEVOFLURANE, VolatileAgent


@dataclass(frozen=True, slots=True)
class BodyPhysiology:
    """Standard adult Gas Man–like body / circuit geometry."""

    circuit_l: float = 8.0
    alveolar_l: float = 2.5
    vrg_l: float = 6.0
    muscle_l: float = 33.0
    fat_l: float = 14.5
    cardiac_output_l_per_min: float = 5.5
    frac_vrg: float = 0.75
    frac_muscle: float = 0.20
    frac_fat: float = 0.05
    alveolar_ventilation_l_per_min: float = 4.0

    def __post_init__(self) -> None:
        flow = self.frac_vrg + self.frac_muscle + self.frac_fat
        if abs(flow - 1.0) > 1e-6:
            raise ValueError("tissue blood-flow fractions must sum to 1")


@dataclass(frozen=True, slots=True)
class VolatileSchedule:
    """Piecewise-constant vaporizer setting and fresh-gas flow."""

    # (start_min, vaporizer_vol_pct, fgf_l_per_min)
    segments: tuple[tuple[float, float, float], ...]

    def at(self, time_min: float) -> tuple[float, float]:
        if not self.segments:
            raise ValueError("schedule must contain at least one segment")
        vap, fgf = self.segments[0][1], self.segments[0][2]
        for start, v, f in self.segments:
            if time_min + 1e-12 >= start:
                vap, fgf = v, f
            else:
                break
        return vap, fgf


@dataclass(frozen=True, slots=True)
class VolatileResult:
    time_min: NDArray[np.float64]
    fi_vol_pct: NDArray[np.float64]
    fa_vol_pct: NDArray[np.float64]
    vrg_vol_pct: NDArray[np.float64]
    muscle_vol_pct: NDArray[np.float64]
    fat_vol_pct: NDArray[np.float64]
    mac_fraction: NDArray[np.float64]

    @property
    def n_samples(self) -> int:
        return int(self.time_min.size)


def simulate_volatile(
    agent: VolatileAgent = SEVOFLURANE,
    schedule: VolatileSchedule | None = None,
    *,
    duration_min: float,
    dt_min: float = 0.05,
    body: BodyPhysiology | None = None,
) -> VolatileResult:
    """Simulate inspired / alveolar / tissue tensions (vol%).

    State is partial-pressure fraction × 100 = vol%. Mixed-venous return and
    tissue uptake use blood:gas and tissue:gas partition coefficients.
    """
    if duration_min <= 0 or dt_min <= 0:
        raise ValueError("duration_min and dt_min must be positive")
    if schedule is None:
        schedule = VolatileSchedule(segments=((0.0, 2.0, 6.0),))

    phys = body if body is not None else BodyPhysiology()
    times = np.arange(0.0, duration_min + dt_min * 0.5, dt_min, dtype=np.float64)
    if times[-1] < duration_min - 1e-12:
        times = np.append(times, duration_min)

    # State as vol% in: circuit, alveoli, VRG, muscle, fat
    y = np.zeros(5, dtype=np.float64)
    out = np.zeros((times.size, 5), dtype=np.float64)
    out[0] = y

    q = phys.cardiac_output_l_per_min
    q_vrg = q * phys.frac_vrg
    q_mus = q * phys.frac_muscle
    q_fat = q * phys.frac_fat
    va = phys.alveolar_ventilation_l_per_min
    lam_b = agent.blood_gas

    for i in range(1, times.size):
        t_prev = float(times[i - 1])
        dt = float(times[i] - t_prev)
        vap, fgf = schedule.at(t_prev)
        y = _rk4_step(y, dt, vap, fgf, phys, agent, q_vrg, q_mus, q_fat, va, lam_b)
        # Partial pressures cannot go negative.
        y = np.maximum(y, 0.0)
        out[i] = y

    vrg = out[:, 2]
    return VolatileResult(
        time_min=times,
        fi_vol_pct=out[:, 0],
        fa_vol_pct=out[:, 1],
        vrg_vol_pct=vrg,
        muscle_vol_pct=out[:, 3],
        fat_vol_pct=out[:, 4],
        mac_fraction=vrg / agent.mac_vol_pct,
    )


def _deriv(
    y: NDArray[np.float64],
    vap: float,
    fgf: float,
    phys: BodyPhysiology,
    agent: VolatileAgent,
    q_vrg: float,
    q_mus: float,
    q_fat: float,
    va: float,
    lam_b: float,
) -> NDArray[np.float64]:
    f_circ, f_a, f_vrg, f_mus, f_fat = y
    q = phys.cardiac_output_l_per_min
    f_v = (q_vrg * f_vrg + q_mus * f_mus + q_fat * f_fat) / q

    # Circuit: FGF delivers vaporizer setting; VA exchanges with alveoli.
    d_circ = (fgf * (vap - f_circ) + va * (f_a - f_circ)) / phys.circuit_l

    # Alveoli: ventilation in, blood uptake out.
    uptake = lam_b * q * (f_a - f_v)
    d_a = (va * (f_circ - f_a) - uptake) / phys.alveolar_l

    # Tissues: dFi/dt = (Qi λb (FA − Fi)) / (Vi λi)
    d_vrg = (q_vrg * lam_b * (f_a - f_vrg)) / (phys.vrg_l * agent.vrg_gas)
    d_mus = (q_mus * lam_b * (f_a - f_mus)) / (phys.muscle_l * agent.muscle_gas)
    d_fat = (q_fat * lam_b * (f_a - f_fat)) / (phys.fat_l * agent.fat_gas)
    return np.array([d_circ, d_a, d_vrg, d_mus, d_fat], dtype=np.float64)


def _rk4_step(
    y: NDArray[np.float64],
    dt: float,
    vap: float,
    fgf: float,
    phys: BodyPhysiology,
    agent: VolatileAgent,
    q_vrg: float,
    q_mus: float,
    q_fat: float,
    va: float,
    lam_b: float,
) -> NDArray[np.float64]:
    def f(state: NDArray[np.float64]) -> NDArray[np.float64]:
        return _deriv(state, vap, fgf, phys, agent, q_vrg, q_mus, q_fat, va, lam_b)

    k1 = f(y)
    k2 = f(y + 0.5 * dt * k1)
    k3 = f(y + 0.5 * dt * k2)
    k4 = f(y + dt * k3)
    return y + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

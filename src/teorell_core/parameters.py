"""Compartmental PK parameter representations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Mammillary3:
    """Three-compartment mammillary model in clearance / volume form.

    Volumes are in litres; clearances are in L/min; ke0 is in 1/min.
    Central compartment is compartment 1.
    """

    v1: float
    v2: float
    v3: float
    cl: float
    q2: float
    q3: float
    ke0: float = 0.0

    def __post_init__(self) -> None:
        for name in ("v1", "v2", "v3", "cl", "q2", "q3"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.ke0 < 0:
            raise ValueError("ke0 must be non-negative")

    def to_micro_rates(self) -> MicroRates:
        return MicroRates(
            k10=self.cl / self.v1,
            k12=self.q2 / self.v1,
            k21=self.q2 / self.v2,
            k13=self.q3 / self.v1,
            k31=self.q3 / self.v3,
            ke0=self.ke0,
            v1=self.v1,
        )


@dataclass(frozen=True, slots=True)
class MicroRates:
    """Micro-rate constants for a 3-compartment model plus optional effect site."""

    k10: float
    k12: float
    k21: float
    k13: float
    k31: float
    ke0: float
    v1: float

    def system_matrix(self) -> NDArray[np.float64]:
        """Continuous-time state matrix for amounts [a1, a2, a3, ae].

        Plasma concentration Cp = a1 / v1.
        Effect-site concentration Ce = ae / v1 (same scaling as plasma).
        """
        k10, k12, k21, k13, k31, ke0 = (
            self.k10,
            self.k12,
            self.k21,
            self.k13,
            self.k31,
            self.ke0,
        )
        return np.array(
            [
                [-(k10 + k12 + k13), k21, k31, 0.0],
                [k12, -k21, 0.0, 0.0],
                [k13, 0.0, -k31, 0.0],
                [ke0, 0.0, 0.0, -ke0],
            ],
            dtype=np.float64,
        )

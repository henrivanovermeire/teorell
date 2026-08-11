"""Dosing events that drive a PK simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Bolus:
    """Instantaneous IV bolus.

    Attributes:
        time_min: Clock time of the bolus (minutes from simulation start).
        amount_mg: Dose in milligrams.
    """

    time_min: float
    amount_mg: float

    def __post_init__(self) -> None:
        if self.time_min < 0:
            raise ValueError("bolus time must be non-negative")
        if self.amount_mg < 0:
            raise ValueError("bolus amount must be non-negative")


@dataclass(frozen=True, slots=True)
class Infusion:
    """Constant-rate IV infusion over an interval.

    Attributes:
        start_min: Infusion start time (minutes).
        duration_min: Infusion duration (minutes).
        rate_mg_per_min: Infusion rate in mg/min.
    """

    start_min: float
    duration_min: float
    rate_mg_per_min: float

    def __post_init__(self) -> None:
        if self.start_min < 0:
            raise ValueError("infusion start must be non-negative")
        if self.duration_min <= 0:
            raise ValueError("infusion duration must be positive")
        if self.rate_mg_per_min < 0:
            raise ValueError("infusion rate must be non-negative")

    @property
    def end_min(self) -> float:
        return self.start_min + self.duration_min

    def rate_at(self, time_min: float) -> float:
        if self.start_min <= time_min < self.end_min:
            return self.rate_mg_per_min
        return 0.0


@dataclass(frozen=True, slots=True)
class Regimen:
    """Collection of bolus and infusion events."""

    boluses: tuple[Bolus, ...] = ()
    infusions: tuple[Infusion, ...] = ()

    def infusion_rate_at(self, time_min: float) -> float:
        return sum(inf.rate_at(time_min) for inf in self.infusions)

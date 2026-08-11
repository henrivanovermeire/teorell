"""Patient covariates used by covariate-adjusted PK models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


@dataclass(frozen=True, slots=True)
class Patient:
    """Anthropometric inputs for PK parameterisation.

    Units: age in years, weight in kg, height in cm.
    """

    age: float
    weight: float
    height: float
    sex: Sex

    def __post_init__(self) -> None:
        if self.age <= 0:
            raise ValueError("age must be positive")
        if self.weight <= 0:
            raise ValueError("weight must be positive")
        if self.height <= 0:
            raise ValueError("height must be positive")

    @property
    def lean_body_mass_kg(self) -> float:
        """James lean body mass (kg)."""
        ratio = self.weight / self.height
        if self.sex is Sex.MALE:
            return 1.1 * self.weight - 128.0 * ratio * ratio
        return 1.07 * self.weight - 148.0 * ratio * ratio

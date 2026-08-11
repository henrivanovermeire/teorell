"""Volatile anesthetic package (Gas Man–style PK)."""

from teorell_core.volatile.gasman import (
    BodyPhysiology,
    VolatileResult,
    VolatileSchedule,
    simulate_volatile,
)
from teorell_core.volatile.properties import (
    AGENTS,
    DESFLURANE,
    HALOTHANE,
    ISOFLURANE,
    SEVOFLURANE,
    VolatileAgent,
)

__all__ = [
    "AGENTS",
    "BodyPhysiology",
    "DESFLURANE",
    "HALOTHANE",
    "ISOFLURANE",
    "SEVOFLURANE",
    "VolatileAgent",
    "VolatileResult",
    "VolatileSchedule",
    "simulate_volatile",
]

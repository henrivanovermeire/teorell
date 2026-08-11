"""teorell-core: pharmacokinetic simulation for anesthesiology & critical care."""

from teorell_core.anesthesia import AnesthesiaResult, simulate_anesthesia
from teorell_core.dosing import Bolus, Infusion, Regimen
from teorell_core.live import LiveSession, LiveSnapshot
from teorell_core.patient import Patient, Sex
from teorell_core.parameters import Mammillary3, MicroRates
from teorell_core.pd import (
    BouillonBIS,
    CombinedBIS,
    SchumacherHypnotic,
    remifentanil_equivalent_ng_per_ml,
)
from teorell_core.simulator import SimulationResult, simulate
from teorell_core.tiva import TivaResult, simulate_tiva
from teorell_core.models import minto_remifentanil, schnider_propofol, scott_alfentanil
from teorell_core.volatile import (
    BodyPhysiology,
    DESFLURANE,
    HALOTHANE,
    ISOFLURANE,
    SEVOFLURANE,
    VolatileAgent,
    VolatileResult,
    VolatileSchedule,
    simulate_volatile,
)

__all__ = [
    "AnesthesiaResult",
    "BodyPhysiology",
    "Bolus",
    "BouillonBIS",
    "CombinedBIS",
    "DESFLURANE",
    "HALOTHANE",
    "ISOFLURANE",
    "Infusion",
    "LiveSession",
    "LiveSnapshot",
    "Mammillary3",
    "MicroRates",
    "Patient",
    "Regimen",
    "SEVOFLURANE",
    "SchumacherHypnotic",
    "Sex",
    "SimulationResult",
    "TivaResult",
    "VolatileAgent",
    "VolatileResult",
    "VolatileSchedule",
    "minto_remifentanil",
    "remifentanil_equivalent_ng_per_ml",
    "schnider_propofol",
    "scott_alfentanil",
    "simulate",
    "simulate_anesthesia",
    "simulate_tiva",
    "simulate_volatile",
]

__version__ = "0.1.0"

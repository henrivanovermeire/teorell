"""Propofol pharmacokinetic models."""

from __future__ import annotations

from teorell_core.parameters import Mammillary3
from teorell_core.patient import Patient

# Schnider TW et al. Anesthesiology 1998;88:1170-82. PMID: 9605675
_KE0_PER_MIN = 0.456


def schnider_propofol(patient: Patient) -> Mammillary3:
    """Schnider et al. propofol model (adult volunteers).

    Returns clearance/volume parameters in L and L/min with effect-site ke0.
    """
    age = patient.age
    weight = patient.weight
    height = patient.height
    lbm = patient.lean_body_mass_kg

    v1 = 4.27
    v2 = 18.9 - 0.391 * (age - 53.0)
    v3 = 238.0

    cl = (
        1.89
        + 0.0456 * (weight - 77.0)
        - 0.0681 * (lbm - 59.0)
        + 0.0264 * (height - 177.0)
    )
    q2 = 1.29 - 0.024 * (age - 53.0)
    q3 = 0.836

    if v2 <= 0 or cl <= 0 or q2 <= 0:
        raise ValueError("Schnider covariates produced non-positive PK parameters")

    return Mammillary3(
        v1=v1,
        v2=v2,
        v3=v3,
        cl=cl,
        q2=q2,
        q3=q3,
        ke0=_KE0_PER_MIN,
    )

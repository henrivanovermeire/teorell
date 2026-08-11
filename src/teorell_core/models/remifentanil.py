"""Remifentanil pharmacokinetic models."""

from __future__ import annotations

from teorell_core.parameters import Mammillary3
from teorell_core.patient import Patient


def minto_remifentanil(patient: Patient) -> Mammillary3:
    """Minto et al. remifentanil model (Anesthesiology 1997;86:10-23).

    Volumes in L, clearances in L/min. When dosing amounts are in µg and rates
    in µg/min, simulated concentrations are in µg/L ≡ ng/mL.
    """
    age = patient.age
    lbm = patient.lean_body_mass_kg
    age_delta = age - 40.0
    lbm_delta = lbm - 55.0

    v1 = 5.1 - 0.0201 * age_delta + 0.072 * lbm_delta
    v2 = 9.82 - 0.0811 * age_delta + 0.108 * lbm_delta
    v3 = 5.42
    cl = 2.6 - 0.0162 * age_delta + 0.0191 * lbm_delta
    q2 = 2.05 - 0.0301 * age_delta
    q3 = 0.076 - 0.00113 * age_delta
    ke0 = 0.595 - 0.007 * age_delta

    for name, value in (
        ("v1", v1),
        ("v2", v2),
        ("v3", v3),
        ("cl", cl),
        ("q2", q2),
        ("q3", q3),
    ):
        if value <= 0:
            raise ValueError(f"Minto covariates produced non-positive {name}={value}")
    if ke0 < 0:
        raise ValueError("Minto covariates produced negative ke0")

    return Mammillary3(v1=v1, v2=v2, v3=v3, cl=cl, q2=q2, q3=q3, ke0=ke0)

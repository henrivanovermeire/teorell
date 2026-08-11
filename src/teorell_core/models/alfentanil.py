"""Alfentanil pharmacokinetic models."""

from __future__ import annotations

from teorell_core.parameters import Mammillary3
from teorell_core.patient import Patient

# Scott JC, Stanski DR. J Pharmacol Exp Ther. 1987;240:159-66.
# Reference volumes/clearances for a ~70 kg adult as tabulated for TCI use
# (e.g. Sigmond et al., BJA 2013;111:197-208). Weight scaling is linear in
# body weight / 70 kg (Stanpump-style "Scott weight-adjusted").
_REF_WEIGHT_KG = 70.0
_V1_REF = 2.19
_V2_REF = 6.7
_V3_REF = 14.52
_CL_REF = 0.195
_Q2_REF = 1.433
_Q3_REF = 0.247
_KE0 = 0.77


def scott_alfentanil(patient: Patient) -> Mammillary3:
    """Scott & Stanski alfentanil model (weight-scaled three-compartment + ke0).

    When dosing amounts are in µg and rates in µg/min, simulated concentrations
    are in µg/L ≡ ng/mL.
    """
    scale = patient.weight / _REF_WEIGHT_KG
    return Mammillary3(
        v1=_V1_REF * scale,
        v2=_V2_REF * scale,
        v3=_V3_REF * scale,
        cl=_CL_REF * scale,
        q2=_Q2_REF * scale,
        q3=_Q3_REF * scale,
        ke0=_KE0,
    )

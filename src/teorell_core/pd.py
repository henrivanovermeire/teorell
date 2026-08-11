"""Pharmacodynamic models linking effect-site concentration to clinical effect."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

# BAS-style equipotency: convert opioid Ce to remifentanil-equivalent ng/mL
# for the Bouillon BIS surface (Connor / Brigham Anesthesia Simulator).
#
# Egan et al., Anesthesiology 1999;90:1260- (ventilatory depression): remifentanil
# is ~40× as potent as alfentanil when both are compared as whole-blood
# concentrations. (Plasma alfentanil vs whole-blood remifentanil is closer to
# ~70×; we use 40:1 as the common educational/simulator whole-blood ratio.)
ALFENTANIL_TO_REMI_EQUIVALENT = 40.0


def remifentanil_equivalent_ng_per_ml(
    *,
    remifentanil_ng_per_ml: ArrayLike | float = 0.0,
    alfentanil_ng_per_ml: ArrayLike | float = 0.0,
) -> NDArray[np.float64]:
    """Sum opioids as remifentanil-equivalent effect-site concentration (ng/mL)."""
    remi = np.asarray(remifentanil_ng_per_ml, dtype=np.float64)
    alf = np.asarray(alfentanil_ng_per_ml, dtype=np.float64)
    if remi.shape == () and alf.shape != ():
        remi = np.full_like(alf, float(remi))
    elif alf.shape == () and remi.shape != ():
        alf = np.full_like(remi, float(alf))
    elif remi.shape != alf.shape:
        raise ValueError("opioid concentration arrays must broadcast or match")
    return remi + alf / ALFENTANIL_TO_REMI_EQUIVALENT


def _as_matching_arrays(
    a: ArrayLike | float,
    b: ArrayLike | float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    if aa.shape == () and bb.shape != ():
        aa = np.full_like(bb, float(aa))
    elif bb.shape == () and aa.shape != ():
        bb = np.full_like(aa, float(bb))
    elif aa.shape != bb.shape:
        raise ValueError("arrays must broadcast or match")
    return aa, bb


@dataclass(frozen=True, slots=True)
class BouillonBIS:
    """Propofol ± opioid → predicted BIS (Bouillon et al. 2004).

    Uses the Minto-type interaction surface as in Brigham Anesthesia Simulator
    (equipotent opioids → remifentanil units, then Bouillon response surface):

        U_p = Ce_propofol / C50_p
        U_r = Ce_opioid_remi_eq / C50_r
        θ   = U_p / (U_p + U_r)
        U   = (U_p + U_r) / (1 - βθ + βθ²)
        BIS = E0 - Emax · U^γ / (1 + U^γ)

    Default parameters match Bouillon et al., Anesthesiology 2004;100:1353-72.

    Units: propofol Ce in µg/mL (= mg/L); opioid Ce as remifentanil-equivalent ng/mL.
    """

    c50_propofol_ug_per_ml: float = 4.47
    c50_remifentanil_ng_per_ml: float = 19.3
    gamma: float = 1.43
    beta: float = 0.0
    e0: float = 97.4
    emax: float = 97.4

    def predict(
        self,
        ce_propofol_ug_per_ml: ArrayLike,
        ce_opioid_remi_eq_ng_per_ml: ArrayLike | float = 0.0,
    ) -> NDArray[np.float64]:
        ce_p = np.asarray(ce_propofol_ug_per_ml, dtype=np.float64)
        ce_r = np.asarray(ce_opioid_remi_eq_ng_per_ml, dtype=np.float64)
        if ce_r.shape == ():
            ce_r = np.full_like(ce_p, float(ce_r))
        if ce_p.shape != ce_r.shape:
            raise ValueError("propofol and opioid Ce arrays must match shape")
        return _hill_bis(
            ce_p / self.c50_propofol_ug_per_ml,
            ce_r / self.c50_remifentanil_ng_per_ml,
            gamma=self.gamma,
            beta=self.beta,
            e0=self.e0,
            emax=self.emax,
        )


@dataclass(frozen=True, slots=True)
class SchumacherHypnotic:
    """Propofol + sevoflurane-equivalent → hypnotic U (Schumacher et al. 2009).

    Additive Greco interaction on BIS for propofol and sevoflurane:
    C50_prop = 3.68 µg/mL, C50_sevo = 1.53 vol%. Other volatiles should be
    converted to sevoflurane-equivalent vol% (MAC scaling) before calling.
    """

    c50_propofol_ug_per_ml: float = 3.68
    c50_sevoflurane_vol_pct: float = 1.53

    def hypnotic_u(
        self,
        ce_propofol_ug_per_ml: ArrayLike | float = 0.0,
        sevoflurane_eq_vol_pct: ArrayLike | float = 0.0,
    ) -> NDArray[np.float64]:
        ce_p, sevo = _as_matching_arrays(ce_propofol_ug_per_ml, sevoflurane_eq_vol_pct)
        return ce_p / self.c50_propofol_ug_per_ml + sevo / self.c50_sevoflurane_vol_pct


@dataclass(frozen=True, slots=True)
class CombinedBIS:
    """BAS-style combined BIS: Schumacher hypnotic U + Bouillon opioid arm.

    When any volatile is present, propofol potency uses Schumacher C50 (3.68).
    Opioids enter as remifentanil-equivalent via the Bouillon Minto surface
    (β=0 → U = U_hypnotic + U_opioid).
    """

    hypnotic: SchumacherHypnotic = SchumacherHypnotic()
    c50_remifentanil_ng_per_ml: float = 19.3
    gamma: float = 1.43
    beta: float = 0.0
    e0: float = 97.4
    emax: float = 97.4

    def predict(
        self,
        *,
        ce_propofol_ug_per_ml: ArrayLike | float = 0.0,
        sevoflurane_eq_vol_pct: ArrayLike | float = 0.0,
        ce_opioid_remi_eq_ng_per_ml: ArrayLike | float = 0.0,
    ) -> NDArray[np.float64]:
        u_h = self.hypnotic.hypnotic_u(ce_propofol_ug_per_ml, sevoflurane_eq_vol_pct)
        remi = np.asarray(ce_opioid_remi_eq_ng_per_ml, dtype=np.float64)
        if remi.shape == ():
            remi = np.full_like(u_h, float(remi))
        elif remi.shape != u_h.shape:
            raise ValueError("opioid array must match hypnotic U shape")
        u_r = remi / self.c50_remifentanil_ng_per_ml
        return _hill_bis(u_h, u_r, gamma=self.gamma, beta=self.beta, e0=self.e0, emax=self.emax)


def _hill_bis(
    up: NDArray[np.float64],
    ur: NDArray[np.float64],
    *,
    gamma: float,
    beta: float,
    e0: float,
    emax: float,
) -> NDArray[np.float64]:
    denom = up + ur
    theta = np.divide(up, denom, out=np.zeros_like(up), where=denom > 0.0)
    u50 = 1.0 - beta * (theta - theta * theta)
    interaction = (up + ur) / np.maximum(u50, 1e-12)
    frac = interaction**gamma / (1.0 + interaction**gamma)
    return e0 - emax * frac

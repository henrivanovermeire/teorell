"""Stateful real-time anesthesia session (stepper for live boluses)."""

from __future__ import annotations

from dataclasses import dataclass, field
import copy

import numpy as np

from teorell_core.models.alfentanil import scott_alfentanil
from teorell_core.models.propofol import schnider_propofol
from teorell_core.models.remifentanil import minto_remifentanil
from teorell_core.patient import Patient
from teorell_core.pd import CombinedBIS, remifentanil_equivalent_ng_per_ml
from teorell_core.simulator import _advance
from teorell_core.volatile.gasman import BodyPhysiology, _rk4_step
from teorell_core.volatile.properties import SEVOFLURANE, VolatileAgent


@dataclass
class LiveSnapshot:
    """One sample from a live session."""

    t_min: float
    bis: float
    propofol_cp: float
    propofol_ce: float
    remifentanil_ce: float
    alfentanil_ce: float
    opioid_remi_eq: float
    fi: float
    fa: float
    vrg: float
    mac: float
    propofol_infusion: float
    remifentanil_infusion: float
    alfentanil_infusion: float
    vaporizer: float
    fgf: float

    def as_dict(self) -> dict[str, float]:
        return {
            "t_min": self.t_min,
            "bis": self.bis,
            "propofol_cp": self.propofol_cp,
            "propofol_ce": self.propofol_ce,
            "remifentanil_ce": self.remifentanil_ce,
            "alfentanil_ce": self.alfentanil_ce,
            "opioid_remi_eq": self.opioid_remi_eq,
            "fi": self.fi,
            "fa": self.fa,
            "vrg": self.vrg,
            "mac": self.mac,
            "propofol_infusion": self.propofol_infusion,
            "remifentanil_infusion": self.remifentanil_infusion,
            "alfentanil_infusion": self.alfentanil_infusion,
            "vaporizer": self.vaporizer,
            "fgf": self.fgf,
        }


@dataclass
class LiveSession:
    """Mutable dual-core session: step(dt), bolus, set infusions / vaporizer."""

    patient: Patient
    volatile_agent: VolatileAgent = SEVOFLURANE
    body: BodyPhysiology = field(default_factory=BodyPhysiology)
    bis_model: CombinedBIS = field(default_factory=CombinedBIS)
    history_limit: int = 3600

    def __post_init__(self) -> None:
        self.t_min = 0.0
        self._prop = schnider_propofol(self.patient)
        self._remi = minto_remifentanil(self.patient)
        self._alf = scott_alfentanil(self.patient)
        self._prop_rates = self._prop.to_micro_rates()
        self._remi_rates = self._remi.to_micro_rates()
        self._alf_rates = self._alf.to_micro_rates()
        self._prop_a = self._prop_rates.system_matrix()
        self._remi_a = self._remi_rates.system_matrix()
        self._alf_a = self._alf_rates.system_matrix()
        self._prop_state = np.zeros(4, dtype=np.float64)
        self._remi_state = np.zeros(4, dtype=np.float64)
        self._alf_state = np.zeros(4, dtype=np.float64)
        self._vol_state = np.zeros(5, dtype=np.float64)
        self.propofol_infusion = 0.0  # mg/min
        self.remifentanil_infusion = 0.0  # µg/min
        self.alfentanil_infusion = 0.0  # µg/min
        self.vaporizer = 0.0  # vol%
        self.fgf = 6.0  # L/min
        self.volatile_enabled = True
        self.history: list[dict[str, float]] = []
        phys = self.body
        q = phys.cardiac_output_l_per_min
        self._q_vrg = q * phys.frac_vrg
        self._q_mus = q * phys.frac_muscle
        self._q_fat = q * phys.frac_fat
        self._va = phys.alveolar_ventilation_l_per_min
        self._lam_b = self.volatile_agent.blood_gas
        self._record()

    def snapshot(self) -> LiveSnapshot:
        prop_cp = float(self._prop_state[0] / self._prop_rates.v1)
        prop_ce = float(self._prop_state[3] / self._prop_rates.v1)
        remi_ce = float(self._remi_state[3] / self._remi_rates.v1)
        alf_ce = float(self._alf_state[3] / self._alf_rates.v1)
        opioid = float(
            remifentanil_equivalent_ng_per_ml(
                remifentanil_ng_per_ml=remi_ce,
                alfentanil_ng_per_ml=alf_ce,
            )
        )
        fi, fa, vrg = (float(x) for x in self._vol_state[:3])
        if not self.volatile_enabled:
            fi = fa = vrg = 0.0
        sevo_eq = self._sevo_eq(vrg)
        bis = float(
            self.bis_model.predict(
                ce_propofol_ug_per_ml=prop_ce,
                sevoflurane_eq_vol_pct=sevo_eq,
                ce_opioid_remi_eq_ng_per_ml=opioid,
            )
        )
        mac = vrg / self.volatile_agent.mac_vol_pct if self.volatile_enabled else 0.0
        return LiveSnapshot(
            t_min=self.t_min,
            bis=bis,
            propofol_cp=prop_cp,
            propofol_ce=prop_ce,
            remifentanil_ce=remi_ce,
            alfentanil_ce=alf_ce,
            opioid_remi_eq=opioid,
            fi=fi,
            fa=fa,
            vrg=vrg,
            mac=mac,
            propofol_infusion=self.propofol_infusion,
            remifentanil_infusion=self.remifentanil_infusion,
            alfentanil_infusion=self.alfentanil_infusion,
            vaporizer=self.vaporizer,
            fgf=self.fgf,
        )

    def copy(self, *, history_limit: int | None = None) -> LiveSession:
        """Return an independent copy suitable for non-mutating forecasts."""
        clone = copy.deepcopy(self)
        if history_limit is not None:
            clone.history_limit = history_limit
            if history_limit <= 0:
                clone.history = []
            elif len(clone.history) > history_limit:
                clone.history = clone.history[-history_limit:]
        return clone

    def step(self, dt_min: float) -> LiveSnapshot:
        if dt_min < 0:
            raise ValueError("dt_min must be non-negative")
        if dt_min > 0:
            self._prop_state = _advance(
                self._prop_state, self._prop_a, self.propofol_infusion, dt_min
            )
            self._remi_state = _advance(
                self._remi_state, self._remi_a, self.remifentanil_infusion, dt_min
            )
            self._alf_state = _advance(
                self._alf_state, self._alf_a, self.alfentanil_infusion, dt_min
            )
            if self.volatile_enabled:
                y = _rk4_step(
                    self._vol_state,
                    dt_min,
                    self.vaporizer,
                    self.fgf,
                    self.body,
                    self.volatile_agent,
                    self._q_vrg,
                    self._q_mus,
                    self._q_fat,
                    self._va,
                    self._lam_b,
                )
                self._vol_state = np.maximum(y, 0.0)
            self.t_min += dt_min
        snap = self.snapshot()
        self._append(snap)
        return snap

    def bolus_propofol(self, amount_mg: float) -> LiveSnapshot:
        if amount_mg < 0:
            raise ValueError("amount must be non-negative")
        self._prop_state = self._prop_state.copy()
        self._prop_state[0] += amount_mg
        snap = self.snapshot()
        self._append(snap)
        return snap

    def bolus_remifentanil(self, amount_ug: float) -> LiveSnapshot:
        if amount_ug < 0:
            raise ValueError("amount must be non-negative")
        self._remi_state = self._remi_state.copy()
        self._remi_state[0] += amount_ug
        snap = self.snapshot()
        self._append(snap)
        return snap

    def bolus_alfentanil(self, amount_ug: float) -> LiveSnapshot:
        if amount_ug < 0:
            raise ValueError("amount must be non-negative")
        self._alf_state = self._alf_state.copy()
        self._alf_state[0] += amount_ug
        snap = self.snapshot()
        self._append(snap)
        return snap

    def set_propofol_infusion(self, rate_mg_per_min: float) -> None:
        if rate_mg_per_min < 0:
            raise ValueError("rate must be non-negative")
        self.propofol_infusion = rate_mg_per_min

    def set_remifentanil_infusion(self, rate_ug_per_min: float) -> None:
        if rate_ug_per_min < 0:
            raise ValueError("rate must be non-negative")
        self.remifentanil_infusion = rate_ug_per_min

    def set_alfentanil_infusion(self, rate_ug_per_min: float) -> None:
        if rate_ug_per_min < 0:
            raise ValueError("rate must be non-negative")
        self.alfentanil_infusion = rate_ug_per_min

    def set_vaporizer(self, vol_pct: float, fgf_l_per_min: float | None = None) -> None:
        if vol_pct < 0:
            raise ValueError("vaporizer % must be non-negative")
        self.vaporizer = vol_pct
        if fgf_l_per_min is not None:
            if fgf_l_per_min <= 0:
                raise ValueError("FGF must be positive")
            self.fgf = fgf_l_per_min

    def reset(self) -> LiveSnapshot:
        self.__post_init__()
        return self.snapshot()

    def _sevo_eq(self, vrg: float) -> float:
        if not self.volatile_enabled or vrg <= 0:
            return 0.0
        agent = self.volatile_agent
        sevo_c50 = SEVOFLURANE.c50_bis_vol_pct
        agent_c50 = agent.c50_bis_vol_pct
        if sevo_c50 is not None and agent_c50 is not None:
            return vrg * (float(sevo_c50) / float(agent_c50))
        return vrg * (SEVOFLURANE.mac_vol_pct / agent.mac_vol_pct)

    def _record(self) -> None:
        self._append(self.snapshot())

    def _append(self, snap: LiveSnapshot) -> None:
        self.history.append(snap.as_dict())
        if len(self.history) > self.history_limit:
            overflow = len(self.history) - self.history_limit
            self.history = self.history[overflow:]

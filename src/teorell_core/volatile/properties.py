"""Volatile anesthetic physicochemical properties (Gas Man–style)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VolatileAgent:
    """Partition coefficients (tissue:gas) and adult MAC.

    Tissue:gas values follow Yasuda et al. / Lowe / Larson as catalogued in the
    README. MAC is the adult ~40-year-old reference (vol%).
    """

    name: str
    blood_gas: float
    vrg_gas: float
    muscle_gas: float
    fat_gas: float
    mac_vol_pct: float
    # Schumacher-style BIS C50 (vol% at VRG/ET). None → scale from sevoflurane MAC.
    c50_bis_vol_pct: float | None = None

    def sevoflurane_equivalent_c50(self, sevo_c50: float = 1.53) -> float:
        """C50 for BIS via MAC scaling when agent-specific C50 is unknown."""
        if self.c50_bis_vol_pct is not None:
            return self.c50_bis_vol_pct
        sevo_mac = 1.85
        return sevo_c50 * (self.mac_vol_pct / sevo_mac)


# Yasuda N et al. Anesth Analg 1989;69:370-3 (sevo/iso/des/halo tissue solubilities).
SEVOFLURANE = VolatileAgent(
    name="sevoflurane",
    blood_gas=0.65,
    vrg_gas=1.15,
    muscle_gas=2.40,
    fat_gas=48.0,
    mac_vol_pct=1.85,
    c50_bis_vol_pct=1.53,  # Schumacher et al. 2009
)

ISOFLURANE = VolatileAgent(
    name="isoflurane",
    blood_gas=1.40,
    vrg_gas=2.10,
    muscle_gas=4.40,
    fat_gas=70.0,
    mac_vol_pct=1.17,
)

DESFLURANE = VolatileAgent(
    name="desflurane",
    blood_gas=0.42,
    vrg_gas=0.54,
    muscle_gas=1.30,
    fat_gas=27.0,
    mac_vol_pct=6.0,
)

HALOTHANE = VolatileAgent(
    name="halothane",
    blood_gas=2.40,
    vrg_gas=4.80,
    muscle_gas=8.00,
    fat_gas=136.0,
    mac_vol_pct=0.75,
)

AGENTS: dict[str, VolatileAgent] = {
    SEVOFLURANE.name: SEVOFLURANE,
    ISOFLURANE.name: ISOFLURANE,
    DESFLURANE.name: DESFLURANE,
    HALOTHANE.name: HALOTHANE,
}

#!/usr/bin/env python3
"""BAS-style sevoflurane Gas Man PK + Schumacher/Bouillon predicted BIS."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from teorell_core import (
    Bolus,
    Infusion,
    Patient,
    Regimen,
    SEVOFLURANE,
    Sex,
    VolatileSchedule,
    simulate_anesthesia,
)


def main() -> None:
    patient = Patient(age=40, weight=70, height=170, sex=Sex.MALE)
    # 3% sevo at 6 L/min FGF for 10 min, then 1.5% maintenance
    schedule = VolatileSchedule(
        segments=(
            (0.0, 3.0, 6.0),
            (10.0, 1.5, 2.0),
        )
    )
    # Optional small propofol bolus at induction
    propofol = Regimen(boluses=(Bolus(0.0, 80.0),))
    remi = Regimen(infusions=(Infusion(1.0, 29.0, 0.15),))  # µg/min

    result = simulate_anesthesia(
        patient,
        propofol=propofol,
        remifentanil=remi,
        volatile_agent=SEVOFLURANE,
        volatile_schedule=schedule,
        duration_min=30.0,
        dt_min=0.1,
    )

    print(f"samples: {result.n_samples}")
    print(f"BIS min  = {result.bis.min():.1f}")
    print(f"MAC max  = {result.mac_fraction.max():.2f}")
    print("time_min  FI    FA    VRG   MAC   BIS")
    for t_show in (0.0, 2.0, 5.0, 10.0, 20.0, 30.0):
        i = int(np.searchsorted(result.time_min, t_show, side="left"))
        i = min(max(i, 0), result.n_samples - 1)
        print(
            f"{result.time_min[i]:8.1f}  "
            f"{result.fi_vol_pct[i]:4.2f}  "
            f"{result.fa_vol_pct[i]:4.2f}  "
            f"{result.vrg_vol_pct[i]:4.2f}  "
            f"{result.mac_fraction[i]:4.2f}  "
            f"{result.bis[i]:5.1f}"
        )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    out = Path(__file__).with_name("sevoflurane_gasman_bis.png")
    fig, (ax_g, ax_b) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))
    ax_g.plot(result.time_min, result.fi_vol_pct, label="FI")
    ax_g.plot(result.time_min, result.fa_vol_pct, label="FA")
    ax_g.plot(result.time_min, result.vrg_vol_pct, label="VRG")
    ax_g.axvline(10.0, color="gray", linestyle="--", linewidth=0.8)
    ax_g.set_ylabel("vol%")
    ax_g.legend(loc="upper right")
    ax_g.set_title("Sevoflurane Gas Man PK + propofol/remi → predicted BIS")

    ax_b.plot(result.time_min, result.bis, color="C2", label="Predicted BIS")
    ax_b.axhspan(40, 60, color="C2", alpha=0.12, label="typical GA band")
    ax_b.set_xlabel("Time (min)")
    ax_b.set_ylabel("BIS")
    ax_b.set_ylim(0, 100)
    ax_b.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

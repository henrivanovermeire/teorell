#!/usr/bin/env python3
"""Example: Schnider propofol — induction bolus plus maintenance infusion."""

from __future__ import annotations

from teorell_core import (
    Bolus,
    Infusion,
    Patient,
    Regimen,
    Sex,
    schnider_propofol,
    simulate,
)


def main() -> None:
    patient = Patient(age=40, weight=70, height=170, sex=Sex.MALE)
    # 100 mg bolus at t=0, then 6 mg/min infusion from 1–60 min
    regimen = Regimen(
        boluses=(Bolus(time_min=0.0, amount_mg=100.0),),
        infusions=(
            Infusion(start_min=1.0, duration_min=59.0, rate_mg_per_min=6.0),
        ),
    )
    result = simulate(
        schnider_propofol(patient),
        regimen,
        duration_min=60.0,
        dt_min=0.1,
    )

    print(f"samples: {result.n_samples}")
    print(f"Cp[0]   = {result.plasma_mg_per_l[0]:.4f} mg/L")
    print(f"Cp[-1]  = {result.plasma_mg_per_l[-1]:.4f} mg/L")
    print(f"Ce[-1]  = {result.effect_site_mg_per_l[-1]:.4f} mg/L")
    print("time_min  Cp_mg_L   Ce_mg_L")
    for t_show in (0.0, 1.0, 5.0, 30.0, 60.0):
        i = int(round(t_show / 0.1))
        i = min(i, result.n_samples - 1)
        print(
            f"{result.time_min[i]:8.1f}  "
            f"{result.plasma_mg_per_l[i]:8.4f}  "
            f"{result.effect_site_mg_per_l[i]:8.4f}"
        )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    from pathlib import Path

    out = Path(__file__).with_name("schnider_bolus_infusion.png")
    plt.plot(result.time_min, result.plasma_mg_per_l, label="Cp")
    plt.plot(result.time_min, result.effect_site_mg_per_l, label="Ce")
    plt.axvline(1.0, color="gray", linestyle="--", linewidth=0.8, label="infusion start")
    plt.xlabel("Time (min)")
    plt.ylabel("Concentration (mg/L)")
    plt.title("Schnider propofol — 100 mg bolus + 6 mg/min infusion")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

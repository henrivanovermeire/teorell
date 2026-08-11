#!/usr/bin/env python3
"""Example: Schnider propofol — several boluses plus a high-rate infusion."""

from __future__ import annotations

from pathlib import Path

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
    # Induction + top-ups, with a high maintenance infusion (≈10 mg/kg/h ≈ 11.7 mg/min)
    regimen = Regimen(
        boluses=(
            Bolus(time_min=0.0, amount_mg=200.0),
            Bolus(time_min=8.0, amount_mg=200.0),
            Bolus(time_min=20.0, amount_mg=200.0),
        ),
        infusions=(
            Infusion(start_min=1.0, duration_min=59.0, rate_mg_per_min=12.0),
        ),
    )
    result = simulate(
        schnider_propofol(patient),
        regimen,
        duration_min=60.0,
        dt_min=0.1,
    )

    print(f"samples: {result.n_samples}")
    print(f"Cp peak = {result.plasma_mg_per_l.max():.4f} mg/L")
    print(f"Cp[-1]  = {result.plasma_mg_per_l[-1]:.4f} mg/L")
    print(f"Ce[-1]  = {result.effect_site_mg_per_l[-1]:.4f} mg/L")
    print("time_min  Cp_mg_L   Ce_mg_L")
    for t_show in (0.0, 1.0, 8.0, 20.0, 30.0, 60.0):
        i = min(int(round(t_show / 0.1)), result.n_samples - 1)
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

    out = Path(__file__).with_name("schnider_multi_bolus_high_infusion.png")
    plt.plot(result.time_min, result.plasma_mg_per_l, label="Cp")
    plt.plot(result.time_min, result.effect_site_mg_per_l, label="Ce")
    for i, t_bolus in enumerate((0.0, 8.0, 20.0)):
        plt.axvline(
            t_bolus,
            color="gray",
            linestyle="--",
            linewidth=0.8,
            label="200 mg boluses" if i == 0 else None,
        )
    plt.xlabel("Time (min)")
    plt.ylabel("Concentration (mg/L)")
    plt.title("Schnider propofol — 3×200 mg boluses + 12 mg/min infusion")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

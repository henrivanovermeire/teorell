#!/usr/bin/env python3
"""TIVA demo: Schnider propofol + Scott alfentanil → Bouillon BIS via remi-eq."""

from __future__ import annotations

from pathlib import Path

from teorell_core import Bolus, Infusion, Patient, Regimen, Sex, simulate_tiva


def main() -> None:
    patient = Patient(age=40, weight=70, height=170, sex=Sex.MALE)

    propofol = Regimen(
        boluses=(Bolus(time_min=0.0, amount_mg=100.0),),
        infusions=(Infusion(start_min=1.0, duration_min=29.0, rate_mg_per_min=6.0),),
    )
    # Alfentanil: µg / µg/min → ng/mL; converted to remi-eq (÷40) for BIS
    alfentanil = Regimen(
        boluses=(Bolus(time_min=0.0, amount_mg=1000.0),),
        infusions=(Infusion(start_min=1.0, duration_min=29.0, rate_mg_per_min=50.0),),
    )

    result = simulate_tiva(
        patient,
        propofol=propofol,
        alfentanil=alfentanil,
        duration_min=30.0,
        dt_min=0.1,
    )

    print(f"samples: {result.n_samples}")
    print(f"BIS[0]   = {result.bis[0]:.1f}")
    print(f"BIS min  = {result.bis.min():.1f}")
    print(f"BIS[-1]  = {result.bis[-1]:.1f}")
    print("time_min  Ce_prop  Ce_alf  remi_eq  BIS")
    for t_show in (0.0, 1.0, 5.0, 15.0, 30.0):
        i = min(int(round(t_show / 0.1)), result.n_samples - 1)
        print(
            f"{result.time_min[i]:8.1f}  "
            f"{result.propofol_ce_ug_per_ml[i]:7.3f}  "
            f"{result.alfentanil_ce_ng_per_ml[i]:7.1f}  "
            f"{result.opioid_remi_eq_ng_per_ml[i]:7.3f}  "
            f"{result.bis[i]:5.1f}"
        )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    out = Path(__file__).with_name("tiva_propofol_alfentanil_bis.png")
    fig, (ax_c, ax_b) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))

    ax_c.plot(result.time_min, result.propofol_ce_ug_per_ml, label="Propofol Ce (µg/mL)")
    ax_c.plot(
        result.time_min,
        result.alfentanil_ce_ng_per_ml / 100.0,
        label="Alfentanil Ce (ng/mL ÷ 100)",
    )
    ax_c.plot(
        result.time_min,
        result.opioid_remi_eq_ng_per_ml,
        label="Opioid remi-eq (ng/mL)",
        linestyle="--",
    )
    ax_c.set_ylabel("Concentration")
    ax_c.legend(loc="upper right")
    ax_c.set_title("TIVA — Schnider propofol + Scott alfentanil → Bouillon BIS")

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

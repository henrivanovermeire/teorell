#!/usr/bin/env python3
"""TIVA demo: Schnider propofol + Minto remifentanil → Bouillon predicted BIS."""

from __future__ import annotations

from pathlib import Path

from teorell_core import Bolus, Infusion, Patient, Regimen, Sex, simulate_tiva


def main() -> None:
    patient = Patient(age=40, weight=70, height=170, sex=Sex.MALE)

    # Propofol: mg / mg/min
    propofol = Regimen(
        boluses=(Bolus(time_min=0.0, amount_mg=100.0),),
        infusions=(Infusion(start_min=1.0, duration_min=29.0, rate_mg_per_min=6.0),),
    )
    # Remifentanil: µg / µg/min  (→ concentrations in ng/mL)
    remifentanil = Regimen(
        boluses=(Bolus(time_min=0.0, amount_mg=50.0),),
        infusions=(Infusion(start_min=1.0, duration_min=29.0, rate_mg_per_min=0.2),),
    )

    result = simulate_tiva(
        patient,
        propofol=propofol,
        remifentanil=remifentanil,
        duration_min=30.0,
        dt_min=0.1,
    )

    print(f"samples: {result.n_samples}")
    print(f"BIS[0]   = {result.bis[0]:.1f}")
    print(f"BIS min  = {result.bis.min():.1f}")
    print(f"BIS[-1]  = {result.bis[-1]:.1f}")
    print("time_min  Cp_prop  Ce_prop  Ce_remi  BIS")
    for t_show in (0.0, 1.0, 5.0, 15.0, 30.0):
        i = min(int(round(t_show / 0.1)), result.n_samples - 1)
        print(
            f"{result.time_min[i]:8.1f}  "
            f"{result.propofol_cp_ug_per_ml[i]:7.3f}  "
            f"{result.propofol_ce_ug_per_ml[i]:7.3f}  "
            f"{result.remifentanil_ce_ng_per_ml[i]:7.3f}  "
            f"{result.bis[i]:5.1f}"
        )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    out = Path(__file__).with_name("tiva_propofol_remifentanil_bis.png")
    fig, (ax_c, ax_b) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))

    ax_c.plot(result.time_min, result.propofol_ce_ug_per_ml, label="Propofol Ce (µg/mL)")
    ax_c.plot(
        result.time_min,
        result.remifentanil_ce_ng_per_ml / 10.0,
        label="Remifentanil Ce (ng/mL ÷ 10)",
    )
    ax_c.set_ylabel("Concentration")
    ax_c.legend(loc="upper right")
    ax_c.set_title("TIVA — Schnider propofol + Minto remifentanil → Bouillon BIS")

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

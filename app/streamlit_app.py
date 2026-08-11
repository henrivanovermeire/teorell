"""teorell Streamlit MVP — interactive BAS-style anesthesia simulator."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from teorell_core import (
    DESFLURANE,
    HALOTHANE,
    ISOFLURANE,
    Bolus,
    Infusion,
    Patient,
    Regimen,
    SEVOFLURANE,
    Sex,
    VolatileSchedule,
    simulate_anesthesia,
)

AGENTS = {
    "Sevoflurane": SEVOFLURANE,
    "Isoflurane": ISOFLURANE,
    "Desflurane": DESFLURANE,
    "Halothane": HALOTHANE,
}


def _regimen(
    *,
    enable: bool,
    bolus_time: float,
    bolus_amount: float,
    inf_start: float,
    inf_duration: float,
    inf_rate: float,
    use_bolus: bool,
    use_infusion: bool,
) -> Regimen | None:
    if not enable:
        return None
    boluses = ()
    infusions = ()
    if use_bolus and bolus_amount > 0:
        boluses = (Bolus(time_min=bolus_time, amount_mg=bolus_amount),)
    if use_infusion and inf_rate > 0 and inf_duration > 0:
        infusions = (
            Infusion(
                start_min=inf_start,
                duration_min=inf_duration,
                rate_mg_per_min=inf_rate,
            ),
        )
    if not boluses and not infusions:
        return None
    return Regimen(boluses=boluses, infusions=infusions)


st.set_page_config(
    page_title="teorell",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("teorell")
st.caption(
    "Educational PK/PD simulator — Schnider / Minto / Scott + Gas Man volatiles → "
    "predicted BIS (Bouillon + Schumacher). Not for clinical use."
)

with st.sidebar:
    st.header("Patient")
    age = st.slider("Age (y)", 18, 90, 40)
    weight = st.slider("Weight (kg)", 40, 150, 70)
    height = st.slider("Height (cm)", 140, 210, 170)
    sex = Sex.MALE if st.radio("Sex", ["Male", "Female"], horizontal=True) == "Male" else Sex.FEMALE

    st.header("Simulation")
    duration = st.slider("Duration (min)", 5, 180, 30)
    dt = st.select_slider("dt (min)", options=[0.05, 0.1, 0.2, 0.5], value=0.1)

    st.header("Propofol (mg)")
    use_prop = st.checkbox("Enable propofol", value=True)
    prop_bolus = st.checkbox("Bolus", value=True, key="prop_b")
    prop_bolus_mg = st.number_input("Bolus amount (mg)", 0.0, 300.0, 100.0, 10.0)
    prop_bolus_t = st.number_input("Bolus time (min)", 0.0, float(duration), 0.0, 0.5, key="prop_bt")
    prop_inf = st.checkbox("Infusion", value=True, key="prop_i")
    prop_rate = st.number_input("Infusion rate (mg/min)", 0.0, 20.0, 6.0, 0.5)
    prop_inf_start = st.number_input("Infusion start (min)", 0.0, float(duration), 1.0, 0.5, key="prop_is")
    prop_inf_dur = st.number_input(
        "Infusion duration (min)",
        0.0,
        float(duration),
        max(duration - 1.0, 0.0),
        1.0,
        key="prop_id",
    )

    st.header("Opioid")
    opioid_choice = st.selectbox("Opioid", ["None", "Remifentanil (µg)", "Alfentanil (µg)"])
    use_remi = opioid_choice.startswith("Remifentanil")
    use_alf = opioid_choice.startswith("Alfentanil")
    op_bolus = st.checkbox("Opioid bolus", value=use_remi or use_alf, key="op_b")
    op_bolus_ug = st.number_input(
        "Bolus (µg)",
        0.0,
        5000.0,
        50.0 if use_remi else 1000.0,
        10.0,
    )
    op_bolus_t = st.number_input("Opioid bolus time (min)", 0.0, float(duration), 0.0, 0.5, key="op_bt")
    op_inf = st.checkbox("Opioid infusion", value=True, key="op_i")
    op_rate = st.number_input(
        "Infusion rate (µg/min)",
        0.0,
        500.0,
        0.2 if use_remi else 50.0,
        0.1,
    )
    op_inf_start = st.number_input("Opioid infusion start (min)", 0.0, float(duration), 1.0, 0.5, key="op_is")
    op_inf_dur = st.number_input(
        "Opioid infusion duration (min)",
        0.0,
        float(duration),
        max(duration - 1.0, 0.0),
        1.0,
        key="op_id",
    )

    st.header("Volatile")
    use_vol = st.checkbox("Enable volatile", value=True)
    agent_name = st.selectbox("Agent", list(AGENTS.keys()))
    vap_ind = st.number_input("Induction vaporizer (%)", 0.0, 12.0, 3.0, 0.1)
    fgf_ind = st.number_input("Induction FGF (L/min)", 0.2, 15.0, 6.0, 0.2)
    t_maint = st.number_input("Switch to maintenance at (min)", 0.0, float(duration), 10.0, 1.0)
    vap_maint = st.number_input("Maintenance vaporizer (%)", 0.0, 12.0, 1.5, 0.1)
    fgf_maint = st.number_input("Maintenance FGF (L/min)", 0.2, 15.0, 2.0, 0.2)

    run = st.button("Run simulation", type="primary", use_container_width=True)

if run or "result" not in st.session_state:
    patient = Patient(age=age, weight=weight, height=height, sex=sex)

    propofol = _regimen(
        enable=use_prop,
        bolus_time=prop_bolus_t,
        bolus_amount=prop_bolus_mg,
        inf_start=prop_inf_start,
        inf_duration=prop_inf_dur,
        inf_rate=prop_rate,
        use_bolus=prop_bolus,
        use_infusion=prop_inf,
    )
    remifentanil = _regimen(
        enable=use_remi,
        bolus_time=op_bolus_t,
        bolus_amount=op_bolus_ug,
        inf_start=op_inf_start,
        inf_duration=op_inf_dur,
        inf_rate=op_rate,
        use_bolus=op_bolus,
        use_infusion=op_inf,
    )
    alfentanil = _regimen(
        enable=use_alf,
        bolus_time=op_bolus_t,
        bolus_amount=op_bolus_ug,
        inf_start=op_inf_start,
        inf_duration=op_inf_dur,
        inf_rate=op_rate,
        use_bolus=op_bolus,
        use_infusion=op_inf,
    )

    vol_schedule = None
    if use_vol:
        segments = [(0.0, vap_ind, fgf_ind)]
        if t_maint > 0 and t_maint < duration:
            segments.append((t_maint, vap_maint, fgf_maint))
        vol_schedule = VolatileSchedule(segments=tuple(segments))

    if propofol is None and remifentanil is None and alfentanil is None and vol_schedule is None:
        st.error("Enable at least one drug or volatile.")
        st.stop()

    try:
        result = simulate_anesthesia(
            patient if (propofol or remifentanil or alfentanil) else None,
            propofol=propofol,
            remifentanil=remifentanil,
            alfentanil=alfentanil,
            volatile_agent=AGENTS[agent_name],
            volatile_schedule=vol_schedule,
            duration_min=float(duration),
            dt_min=float(dt),
        )
        st.session_state["result"] = result
        st.session_state["agent_name"] = agent_name
    except Exception as exc:  # noqa: BLE001 — show in UI
        st.exception(exc)
        st.stop()

result = st.session_state["result"]
agent_name = st.session_state.get("agent_name", "Sevoflurane")

c1, c2, c3, c4 = st.columns(4)
c1.metric("BIS min", f"{result.bis.min():.1f}")
c2.metric("BIS final", f"{result.bis[-1]:.1f}")
c3.metric("MAC max", f"{result.mac_fraction.max():.2f}")
c4.metric("VRG max (vol%)", f"{result.vrg_vol_pct.max():.2f}")

bis_df = pd.DataFrame({"time_min": result.time_min, "BIS": result.bis}).set_index("time_min")
st.subheader("Predicted BIS")
st.line_chart(bis_df, height=280)
st.caption("Shaded clinical target is typically 40–60 during general anesthesia (educational only).")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("IV effect-site")
    iv_df = pd.DataFrame(
        {
            "time_min": result.time_min,
            "Propofol Ce (µg/mL)": result.propofol_ce_ug_per_ml,
            "Opioid remi-eq (ng/mL)": result.opioid_remi_eq_ng_per_ml,
        }
    ).set_index("time_min")
    st.line_chart(iv_df, height=280)

with col_b:
    st.subheader(f"Volatile tensions ({agent_name})")
    vol_df = pd.DataFrame(
        {
            "time_min": result.time_min,
            "FI (vol%)": result.fi_vol_pct,
            "FA (vol%)": result.fa_vol_pct,
            "VRG (vol%)": result.vrg_vol_pct,
        }
    ).set_index("time_min")
    st.line_chart(vol_df, height=280)

with st.expander("MAC fraction"):
    mac_df = pd.DataFrame(
        {"time_min": result.time_min, "MAC fraction": result.mac_fraction}
    ).set_index("time_min")
    st.line_chart(mac_df, height=220)

st.divider()
st.markdown(
    "**Models:** Schnider propofol · Minto remifentanil · Scott alfentanil · "
    "Gas Man–style volatiles · Bouillon / Schumacher predicted BIS. "
    "This is an educational FOSS tool, not a medical device."
)

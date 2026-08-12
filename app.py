# ─────────────────────────────────────────────
#  app.py  —  Streamlit Dashboard (Full Featured)
# ─────────────────────────────────────────────
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import optuna

from simulation  import run_simulation
from adversarial import run_red_team
from remedial    import get_remediation_stream
from tank_visual import build_tank_html
from config import (
    SETPOINT_H2, TANK1_MAX_HEIGHT, TANK2_MAX_HEIGHT,
    N_OPTUNA_TRIALS, GEMINI_API_KEY,
    PID_KP, PID_KI, PID_KD,
)

# ══════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="2-Tank Red Team",
    page_icon="🧪",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;600;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Exo 2', sans-serif;
    background: #0a0e1a;
    color: #c8d6f0;
}
h1, h2, h3 { font-family: 'Share Tech Mono', monospace; }
.stApp { background: #0a0e1a; }
[data-testid="stSidebar"] {
    background: #0d1321;
    border-right: 1px solid #1e3a5f;
}
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #c0392b, #8e1010);
    color: white;
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 2px;
    border: none;
    border-radius: 4px;
    padding: 0.7rem 2rem;
    width: 100%;
    text-transform: uppercase;
    box-shadow: 0 0 20px #c0392b55;
    transition: all 0.2s;
}
div[data-testid="stButton"] > button:hover { box-shadow: 0 0 35px #c0392baa; transform: translateY(-1px); }
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 0.5rem 1rem;
}
[data-testid="stMetricValue"] { font-family: 'Share Tech Mono', monospace; color: #38bdf8; }
.stProgress > div > div { background: linear-gradient(90deg, #c0392b, #e74c3c); }
.attack-table {
    background: #111827; border: 1px solid #7f1d1d;
    border-radius: 6px; padding: 1rem 1.5rem;
    font-family: 'Share Tech Mono', monospace; font-size: 0.85rem; color: #fca5a5; margin: 0.5rem 0;
}
.section-header {
    font-family: 'Share Tech Mono', monospace; font-size: 0.75rem;
    letter-spacing: 3px; color: #64748b; text-transform: uppercase;
    margin: 1.5rem 0 0.5rem 0; border-bottom: 1px solid #1e293b; padding-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  CHART HELPERS
# ══════════════════════════════════════════════

PARAM_LABELS = {
    "valve1_clog"  : "Valve-1 Clog",
    "valve2_clog"  : "Valve-2 Clog",
    "leak_rate"    : "Leak Rate",
    "sensor_bias"  : "Sensor Bias",
    "sensor_noise" : "Sensor Noise",
    "inlet_surge"  : "Pump Surge",
}


def make_tank_figure(result: dict, setpoint: float, title_suffix="",
                     show_failure_events=False) -> go.Figure:
    t  = result["time"]
    h1 = result["h1"]
    h2 = result["h2"]

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=(
            "Tank 1 — Level (m)",
            f"Tank 2 — Level (m)  [Setpoint = {setpoint:.2f} m]",
            "Flow Rates (m³/s)",
        ),
    )

    fig.add_trace(go.Scatter(x=t, y=h1, name="h₁", line=dict(color="#38bdf8", width=2)), row=1, col=1)
    fig.add_hline(y=TANK1_MAX_HEIGHT, line=dict(color="#ef4444", dash="dash", width=1.5),
                  annotation_text=f"T1 max {TANK1_MAX_HEIGHT}m", annotation_position="top right", row=1, col=1)

    fig.add_trace(go.Scatter(x=t, y=h2, name="h₂", line=dict(color="#a78bfa", width=2)), row=2, col=1)
    fig.add_hline(y=setpoint, line=dict(color="#22d3ee", dash="dot", width=1.5),
                  annotation_text=f"SP={setpoint:.2f}m", annotation_position="top right", row=2, col=1)
    fig.add_hline(y=TANK2_MAX_HEIGHT, line=dict(color="#ef4444", dash="dash", width=1.5),
                  annotation_text=f"T2 max {TANK2_MAX_HEIGHT}m", annotation_position="top right", row=2, col=1)

    fig.add_trace(go.Scatter(x=t, y=result["q_in"],  name="Q_in",  line=dict(color="#34d399", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=t, y=result["q12"],   name="Q_12",  line=dict(color="#fbbf24", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=t, y=result["q_out"], name="Q_out", line=dict(color="#f87171", width=1.5)), row=3, col=1)

    # ── Failure event vertical lines ──────────────
    if show_failure_events:
        t1_ov = result.get("overflow_t1_time")
        t2_ov = result.get("overflow_t2_time")
        if t1_ov is not None:
            fig.add_vline(x=t1_ov, line=dict(color="#ef4444", width=2, dash="dot"),
                          annotation_text=f"T1 overflow @{t1_ov:.0f}s",
                          annotation_font_color="#ef4444", row=1, col=1)
        if t2_ov is not None:
            fig.add_vline(x=t2_ov, line=dict(color="#f97316", width=2, dash="dot"),
                          annotation_text=f"T2 overflow @{t2_ov:.0f}s",
                          annotation_font_color="#f97316", row=2, col=1)
        # Annotate when steady-state deviation starts (last 30s check window)
        steady_start = max(0, t[-1] - 30)
        fig.add_vrect(x0=steady_start, x1=t[-1],
                      fillcolor="rgba(239,68,68,0.05)",
                      line_width=0,
                      annotation_text="Steady-state window",
                      annotation_font_color="#64748b",
                      row=2, col=1)

    fig.update_layout(
        title=dict(text=f"<b>2-Tank System Response</b>  {title_suffix}",
                   font=dict(family="Share Tech Mono", size=14, color="#94a3b8")),
        height=620, paper_bgcolor="#0a0e1a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8", family="Exo 2"),
        legend=dict(bgcolor="#111827", bordercolor="#1e3a5f", borderwidth=1),
        xaxis3=dict(title="Time (s)"),
        margin=dict(l=50, r=30, t=70, b=40),
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="#1e293b", row=i, col=1)
        fig.update_yaxes(gridcolor="#1e293b", row=i, col=1)
    return fig


def make_optuna_figure(all_damages: list) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(all_damages) + 1)), y=all_damages,
        mode="lines+markers", name="Damage Score",
        line=dict(color="#f97316", width=2), marker=dict(size=4, color="#ef4444"),
    ))
    running_max = np.maximum.accumulate(all_damages)
    fig.add_trace(go.Scatter(
        x=list(range(1, len(all_damages) + 1)), y=running_max,
        mode="lines", name="Best so far",
        line=dict(color="#ef4444", width=2, dash="dot"),
    ))
    fig.update_layout(
        title=dict(text="<b>Adversarial Search Progress</b>",
                   font=dict(family="Share Tech Mono", size=13, color="#94a3b8")),
        xaxis_title="Trial #", yaxis_title="Damage Score", height=280,
        paper_bgcolor="#0a0e1a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8"),
        legend=dict(bgcolor="#111827", bordercolor="#1e3a5f", borderwidth=1),
        margin=dict(l=50, r=30, t=50, b=40),
    )
    fig.update_xaxes(gridcolor="#1e293b")
    fig.update_yaxes(gridcolor="#1e293b")
    return fig


def make_importance_heatmap(study: optuna.Study) -> go.Figure:
    """fANOVA-based parameter importance from Optuna."""
    try:
        importances = optuna.importance.get_param_importances(study)
    except Exception:
        # Fallback: use correlation with objective
        trials = study.trials
        data = {p: [t.params.get(p, 0) for t in trials if t.value is not None] for p in ATTACK_SPACE_KEYS}
        damages = [-t.value for t in trials if t.value is not None]
        importances = {}
        for p, vals in data.items():
            if len(vals) > 2:
                corr = np.corrcoef(vals, damages)[0, 1]
                importances[p] = abs(corr)

    labels = [PARAM_LABELS.get(k, k) for k in importances.keys()]
    values = list(importances.values())

    # Normalize to 0-100
    total = sum(values) if sum(values) > 0 else 1
    pct = [v / total * 100 for v in values]

    # Sort descending
    sorted_pairs = sorted(zip(labels, pct), key=lambda x: x[1], reverse=True)
    labels_s, pct_s = zip(*sorted_pairs) if sorted_pairs else ([], [])

    # Color by danger level
    colors = ["#ef4444" if p > 30 else "#f97316" if p > 15 else "#fbbf24" if p > 5 else "#34d399"
              for p in pct_s]

    fig = go.Figure(go.Bar(
        y=list(labels_s), x=list(pct_s),
        orientation="h",
        marker_color=colors,
        text=[f"{p:.1f}%" for p in pct_s],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="<b>⚡ Parameter Importance (fANOVA)</b>  — What the attacker relied on most",
                   font=dict(family="Share Tech Mono", size=13, color="#94a3b8")),
        xaxis_title="Importance (%)",
        yaxis=dict(autorange="reversed"),
        height=320, paper_bgcolor="#0a0e1a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8", family="Exo 2"),
        margin=dict(l=130, r=80, t=60, b=40),
        xaxis=dict(gridcolor="#1e293b", range=[0, max(pct_s) * 1.25] if pct_s else [0, 100]),
    )
    return fig


def make_tornado_chart(setpoint: float) -> go.Figure:
    """One-at-a-time sensitivity: how much does each param increase damage?"""
    from adversarial import _objective
    from config import ATTACK_SPACE

    nominal_result = run_simulation(setpoint=setpoint)
    nominal_damage = nominal_result["rmse"] + nominal_result["max_setpt_err"]

    param_defaults = {k: (v[0] + v[1]) / 2 for k, v in ATTACK_SPACE.items()}
    # Use zero/nominal for the "off" state
    param_off = {
        "valve1_clog": 0.0, "valve2_clog": 0.0,
        "leak_rate": 0.0, "sensor_bias": 0.0,
        "sensor_noise": 0.0, "inlet_surge": 1.0,
    }

    deltas = {}
    for param, (lo, hi) in ATTACK_SPACE.items():
        args_max = dict(param_off)
        args_max[param] = hi
        res_max = run_simulation(setpoint=setpoint, **args_max)
        damage_max = res_max["rmse"] + res_max["max_setpt_err"]
        if res_max["overflow_t1"]: damage_max += 10
        if res_max["overflow_t2"]: damage_max += 10
        deltas[param] = damage_max - nominal_damage

    sorted_params = sorted(deltas.items(), key=lambda x: x[1])
    labels = [PARAM_LABELS.get(k, k) for k, _ in sorted_params]
    vals   = [v for _, v in sorted_params]
    colors = ["#ef4444" if v > 5 else "#f97316" if v > 1 else "#fbbf24" for v in vals]

    fig = go.Figure(go.Bar(
        y=labels, x=vals, orientation="h",
        marker_color=colors,
        text=[f"+{v:.3f}" for v in vals], textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="<b>🌪 Tornado Chart</b>  — Individual parameter effect on damage",
                   font=dict(family="Share Tech Mono", size=13, color="#94a3b8")),
        xaxis_title="Damage increase (min→max, others nominal)",
        height=300, paper_bgcolor="#0a0e1a", plot_bgcolor="#0f172a",
        font=dict(color="#94a3b8", family="Exo 2"),
        margin=dict(l=130, r=80, t=60, b=40),
        xaxis=dict(gridcolor="#1e293b"),
        yaxis=dict(gridcolor="#1e293b"),
    )
    return fig


def make_top5_table(study: optuna.Study, setpoint: float) -> pd.DataFrame:
    """Top 5 worst (highest damage) attack parameter combinations."""
    trials = sorted(
        [t for t in study.trials if t.value is not None],
        key=lambda t: t.value   # Optuna minimises -damage
    )[:5]

    rows = []
    for i, trial in enumerate(trials):
        p = trial.params
        rows.append({
            "Rank"          : i + 1,
            "Damage Score"  : f"{-trial.value:.2f}",
            "V1 Clog %"     : f"{p.get('valve1_clog',0)*100:.0f}%",
            "V2 Clog %"     : f"{p.get('valve2_clog',0)*100:.0f}%",
            "Leak (m³/s)"   : f"{p.get('leak_rate',0):.4f}",
            "Sensor Bias"   : f"{p.get('sensor_bias',0):+.3f}m",
            "Noise σ"       : f"{p.get('sensor_noise',0):.3f}m",
            "Surge ×"       : f"{p.get('inlet_surge',1):.2f}",
        })
    return pd.DataFrame(rows)


ATTACK_SPACE_KEYS = ["valve1_clog", "valve2_clog", "leak_rate",
                     "sensor_bias", "sensor_noise", "inlet_surge"]


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    st.divider()

    if GEMINI_API_KEY:
        st.success("🔑 Gemini API key loaded", icon="✅")
    else:
        st.warning("⚠️ GEMINI_API_KEY not set in .env", icon="⚠️")

    st.divider()
    st.markdown("**Nominal Operating Point**")
    setpoint = st.slider("Tank 2 Setpoint (m)", 0.3, 1.4, SETPOINT_H2, 0.05)

    st.divider()
    st.markdown("**Red-Team Budget**")
    n_trials = st.slider("Optuna Trials", 20, 150, N_OPTUNA_TRIALS, 10)

    st.divider()
    st.markdown("**Attack Search Space**")
    st.caption("Valve clog : 0 – 90 %")
    st.caption("Leak rate  : 0 – 0.02 m³/s")
    st.caption("Sensor bias: ±0.3 m")
    st.caption("Pump surge : 1× – 3×")

    st.divider()
    st.markdown("**🔧 PID Tuning (Experiment)**")
    st.caption("Adjust PID before launching to test resilience")
    kp_override = st.slider("Kp", 0.5, 6.0, PID_KP, 0.1)
    ki_override = st.slider("Ki", 0.1, 2.0, PID_KI, 0.05)
    kd_override = st.slider("Kd", 0.0, 0.5, PID_KD, 0.01)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
st.markdown(
    "<h1 style='font-family:Share Tech Mono;color:#ef4444;letter-spacing:3px;margin-bottom:0;'>"
    "⚠ TWO-TANK RED TEAM CONSOLE</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#475569;font-size:0.85rem;margin-top:2px;'>"
    "Adversarial AI stress-testing for process-control safety | ISA-84 aligned</p>",
    unsafe_allow_html=True)
st.divider()

# ── Nominal baseline ────────────────────────────
st.markdown("<div class='section-header'>NOMINAL BASELINE</div>", unsafe_allow_html=True)

# Apply PID overrides for nominal preview
import config as _cfg
_cfg.PID_KP = kp_override
_cfg.PID_KI = ki_override
_cfg.PID_KD = kd_override

nominal = run_simulation(setpoint=setpoint)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Peak h₁", f"{nominal['max_h1']:.3f} m")
c2.metric("Peak h₂", f"{nominal['max_h2']:.3f} m")
c3.metric("RMSE",    f"{nominal['rmse']:.4f} m")
c4.metric("Steady err", f"{nominal['steady_err']:.4f} m")

# Warn if not settling near setpoint
if nominal['steady_err'] > 0.1:
    st.warning(f"⚠️ Nominal simulation not settling near setpoint ({setpoint:.2f} m). "
               f"Steady-state error = {nominal['steady_err']:.3f} m. "
               f"Try reducing Kd or check CV2_NOMINAL in config.", icon="⚠️")

st.plotly_chart(make_tank_figure(nominal, setpoint, "— Nominal (no attack)"),
                use_container_width=True, key="chart_nominal")

with st.expander("🖥️ Animated Tank View — Nominal", expanded=False):
    import streamlit.components.v1 as components
    components.html(build_tank_html(nominal, setpoint, h1_max=2.0, h2_max=1.5), height=330)

# ── Red Team Button ─────────────────────────────
st.divider()
launch_btn = st.button("🔴  LAUNCH RED-TEAM STRESS TEST")

if launch_btn:
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY is missing. Add it to your .env file and restart.")
        st.stop()

    st.markdown("<div class='section-header'>ADVERSARIAL SEARCH IN PROGRESS…</div>",
                unsafe_allow_html=True)
    progress_bar  = st.progress(0)
    progress_text = st.empty()
    optuna_chart  = st.empty()

    damage_log = []

    def progress_cb(done, total, score):
        damage_log.append(score)
        frac = done / total
        progress_bar.progress(frac)
        progress_text.markdown(
            f"<span style='font-family:Share Tech Mono;color:#f97316;'>"
            f"Trial {done}/{total}  |  Best damage: {max(damage_log):.2f}</span>",
            unsafe_allow_html=True)
        if len(damage_log) > 1:
            optuna_chart.plotly_chart(
                make_optuna_figure(damage_log), use_container_width=True,
                key=f"optuna_live_{len(damage_log)}")

    _cfg.N_OPTUNA_TRIALS = n_trials

    with st.spinner("Red-team agent searching for worst-case scenario…"):
        report = run_red_team(setpoint=setpoint, progress_callback=progress_cb)

    progress_bar.progress(1.0)
    progress_text.markdown(
        f"<span style='font-family:Share Tech Mono;color:#ef4444;font-weight:700;'>"
        f"✅ SEARCH COMPLETE — Worst damage score: {report['damage_score']:.2f}</span>",
        unsafe_allow_html=True)

    optuna_chart.plotly_chart(
        make_optuna_figure(report["all_damages"]),
        use_container_width=True, key="optuna_final")

    # ── A. Parameter Importance Heatmap ───────────────────────────
    st.markdown("<div class='section-header'>A. PARAMETER IMPORTANCE  (fANOVA — what the attacker exploited)</div>",
                unsafe_allow_html=True)
    col_imp, col_torn = st.columns(2)
    with col_imp:
        st.plotly_chart(make_importance_heatmap(report["study"]),
                        use_container_width=True, key="importance_chart")
        st.caption("🔴 Red = critical fix priority  |  🟠 Orange = high  |  🟡 Yellow = medium  |  🟢 Green = low")
    with col_torn:
        with st.spinner("Computing one-at-a-time sensitivity…"):
            st.plotly_chart(make_tornado_chart(setpoint),
                            use_container_width=True, key="tornado_chart")
        st.caption("Each bar = damage increase when one parameter goes from nominal → worst-case")

    # ── D. Top-5 Attack Scenarios ──────────────────────────────────
    st.markdown("<div class='section-header'>D. TOP-5 WORST ATTACK SCENARIOS</div>",
                unsafe_allow_html=True)
    top5_df = make_top5_table(report["study"], setpoint)
    st.dataframe(
        top5_df.style.highlight_max(subset=["Damage Score"], color="#7f1d1d")
                     .set_properties(**{"background-color": "#111827", "color": "#fca5a5",
                                        "border-color": "#1e3a5f"}),
        use_container_width=True, hide_index=True,
    )
    st.caption("Multiple attack routes to failure — each row represents an independent path the adversary found.")

    # ── Worst-case simulation plot with failure timeline ───────────
    st.markdown("<div class='section-header'>WORST-CASE ATTACK SIMULATION  (with failure timeline)</div>",
                unsafe_allow_html=True)

    wr = report["worst_result"]
    wp = report["worst_params"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Peak h₁", f"{wr['max_h1']:.3f} m",
                delta=f"+{wr['max_h1']-nominal['max_h1']:.3f}", delta_color="inverse")
    col2.metric("Peak h₂", f"{wr['max_h2']:.3f} m",
                delta=f"+{wr['max_h2']-nominal['max_h2']:.3f}", delta_color="inverse")
    col3.metric("RMSE", f"{wr['rmse']:.4f} m",
                delta=f"+{wr['rmse']-nominal['rmse']:.4f}", delta_color="inverse")
    col4.metric("T1 Overflow", "YES ⚠️" if wr["overflow_t1"] else "No")

    st.plotly_chart(
        make_tank_figure(wr, setpoint,
                         "— <span style='color:#ef4444;'>WORST-CASE ATTACK</span>",
                         show_failure_events=True),
        use_container_width=True, key="chart_worst_case")

    with st.expander("🖥️ Animated Tank View — Worst-Case Attack", expanded=True):
        components.html(build_tank_html(wr, setpoint, h1_max=2.0, h2_max=1.5), height=330)

    # Failure event callouts
    if wr.get("overflow_t1_time") is not None:
        st.error(f"⏱ Tank 1 overflow first occurred at **t = {wr['overflow_t1_time']:.0f} s**  |  "
                 f"Total spill: **{wr.get('total_spill1_m3', 0):.4f} m³**")
    if wr.get("overflow_t2_time") is not None:
        st.error(f"⏱ Tank 2 overflow first occurred at **t = {wr['overflow_t2_time']:.0f} s**  |  "
                 f"Total spill: **{wr.get('total_spill2_m3', 0):.4f} m³**")

    # ── Attack params table ────────────────────────
    st.markdown("<div class='section-header'>WORST-CASE ATTACK PARAMETERS</div>",
                unsafe_allow_html=True)
    st.markdown(f"""
<div class='attack-table'>
  Valve-1 clogging : <b>{wp['valve1_clog']*100:.1f}%</b><br>
  Valve-2 clogging : <b>{wp['valve2_clog']*100:.1f}%</b><br>
  Tank-1 leak rate : <b>{wp['leak_rate']:.5f} m³/s</b><br>
  Sensor bias (h₂) : <b>{wp['sensor_bias']:+.4f} m</b><br>
  Sensor noise (σ) : <b>{wp['sensor_noise']:.4f} m</b><br>
  Inlet pump surge : <b>{wp['inlet_surge']:.3f}×</b>
</div>""", unsafe_allow_html=True)

    # ── Failure modes ──────────────────────────────
    st.markdown("<div class='section-header'>IDENTIFIED FAILURE MODES</div>", unsafe_allow_html=True)
    for fm in report["failure_modes"]:
        st.error(f"❌  {fm}")

    # ── E. PID Re-tuning Widget ────────────────────
    st.markdown("<div class='section-header'>E. PID RESILIENCE CHECK — RE-RUN WORST ATTACK WITH TUNED PID</div>",
                unsafe_allow_html=True)
    st.info("💡 You adjusted Kp/Ki/Kd in the sidebar. The result below shows if your PID tuning "
            "survives the same worst-case attack.")

    pid_rerun = run_simulation(setpoint=setpoint, **wp)
    pid_survived = not (pid_rerun["overflow_t1"] or pid_rerun["overflow_t2"]) and pid_rerun["steady_err"] < 0.1

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("RMSE (tuned PID)", f"{pid_rerun['rmse']:.4f} m",
               delta=f"{pid_rerun['rmse']-wr['rmse']:+.4f}", delta_color="inverse")
    rc2.metric("Steady err (tuned)", f"{pid_rerun['steady_err']:.4f} m",
               delta=f"{pid_rerun['steady_err']-wr['steady_err']:+.4f}", delta_color="inverse")
    rc3.metric("Survived attack?", "✅ YES" if pid_survived else "❌ NO")

    if pid_survived:
        st.success(f"✅ PID Kp={kp_override} / Ki={ki_override} / Kd={kd_override} — "
                   f"Survives worst-case attack without overflow.")
    else:
        st.warning(f"⚠️ PID Kp={kp_override} / Ki={ki_override} / Kd={kd_override} — "
                   f"Still fails under worst-case attack. Try increasing Kp or Ki.")

    st.plotly_chart(
        make_tank_figure(pid_rerun, setpoint,
                         f"— Worst attack, tuned PID (Kp={kp_override}/Ki={ki_override}/Kd={kd_override})",
                         show_failure_events=True),
        use_container_width=True, key="chart_pid_rerun")

    with st.expander("🖥️ Animated Tank View — PID Resilience Check", expanded=False):
        components.html(build_tank_html(pid_rerun, setpoint, h1_max=2.0, h2_max=1.5), height=330)

    # ── Gemini Remediation ─────────────────────────
    st.markdown("<div class='section-header'>AI REMEDIAL AGENT — ENGINEERING REPORT</div>",
                unsafe_allow_html=True)

    remediation_placeholder = st.empty()
    full_text = ""

    with st.spinner("Consulting Gemini remedial agent…"):
        try:
            for chunk in get_remediation_stream(report, setpoint):
                full_text += chunk
                remediation_placeholder.markdown(full_text + "▌")
            remediation_placeholder.markdown(full_text)
        except Exception as e:
            st.error(f"Gemini error: {e}")

    st.divider()
    st.markdown("""
<p style='text-align:center;color:#334155;font-size:0.75rem;font-family:Share Tech Mono;'>
2-TANK RED TEAM CONSOLE — Adversarial AI × Process Safety × ISA-84
</p>""", unsafe_allow_html=True)
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import subprocess
import random
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ops1 Validation Dashboard",
    page_icon="🤖",
    layout="wide",
)

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "Results"
RUNNER_PATH = BASE_DIR / "test_runner.py"

DARK = "plotly_dark"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("ops1")
    st.caption("Simulation Validation Framework")
    st.divider()

    # Re-run button
    if st.button("▶ Re-run test_runner.py", use_container_width=True):
        with st.spinner("Running test suite..."):
            result = subprocess.run(
                ["python", str(RUNNER_PATH)],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR),
            )
        if result.returncode == 0:
            st.success("Run complete.")
        else:
            st.error("Run failed.")
            st.code(result.stderr)
        st.rerun()

    st.divider()

    # File picker
    csv_files = sorted(RESULTS_DIR.glob("*.csv"), reverse=True) if RESULTS_DIR.exists() else []

    if not csv_files:
        st.info("No results found — showing demo data. Run test_runner.py to load real results.")

    selected_file = st.selectbox(
        "Result file",
        options=csv_files if csv_files else ["demo"],
        format_func=lambda p: p.name if p != "demo" else "demo_run.csv",
    )

# ── Load data ─────────────────────────────────────────────────────────────────
DEMO_MODE = selected_file == "demo"

if DEMO_MODE:
    rng = random.Random(42)
    scenarios = {
        "SCN_001": ("TestBox",      20.0, 6.0, 0.80),
        "SCN_002": ("TestCylinder", 20.0, 6.0, 0.75),
        "SCN_003": ("TestSphere",   20.0, 5.0, 0.70),
        "SCN_004": ("TestBox",      10.0, 5.0, 0.55),
        "SCN_005": ("TestCylinder", 10.0, 5.0, 0.50),
        "SCN_006": ("TestSphere",   10.0, 6.0, 0.45),
    }
    FAILURE_TAGS = ["PLACEMENT_MISS", "GRASP_FAIL", "TIMEOUT", "DROP_IN_TRANSIT"]
    rows = []
    for scn_id, (obj, tol, max_t, p_pass) in scenarios.items():
        for trial in range(1, 6):
            success = rng.random() < p_pass
            if success:
                err = rng.uniform(0, tol * 0.8)
                cyc = rng.uniform(1.5, max_t * 0.85)
                tag = "NONE"
            else:
                err = rng.uniform(tol * 0.9, tol * 2.5)
                cyc = rng.uniform(max_t * 0.7, max_t * 1.1)
                tag = rng.choice(FAILURE_TAGS)
            rows.append(dict(
                scenario_id=scn_id, object=obj, trial=trial,
                success=success, placement_error_mm=round(err, 2),
                cycle_time_s=round(cyc, 3), failure_tag=tag,
                placement_tolerance_mm=tol, max_cycle_time_s=max_t,
            ))
    df = pd.DataFrame(rows)
    run_ts = "demo"
else:
    df = pd.read_csv(selected_file)
    df["success"] = df["success"].astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    try:
        ts_str = selected_file.stem.replace("run_", "")
        run_ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        run_ts = "unknown"

# ── Header ────────────────────────────────────────────────────────────────────
st.title("ops1 Validation Dashboard")
if DEMO_MODE:
    st.caption("**File:** demo_run.csv   |   **Run:** demo")
    st.warning("Demo mode — showing synthetic data. Run test_runner.py and reload to see real results.")
else:
    st.caption(f"**File:** {selected_file.name}   |   **Run:** {run_ts}")
st.divider()

# ── Section 1 — KPIs ──────────────────────────────────────────────────────────
pass_rate = df["success"].mean() * 100
total_trials = len(df)
avg_error = df["placement_error_mm"].mean()
avg_time = df["cycle_time_s"].mean()

if pass_rate >= 70:
    rate_color = "#2ecc71"
elif pass_rate >= 50:
    rate_color = "#f39c12"
else:
    rate_color = "#e74c3c"

k1, k2, k3, k4 = st.columns(4)

def kpi_card(col, label, value, color="#ffffff"):
    col.markdown(
        f"""
        <div style="background:#1e1e2e;border-radius:10px;padding:20px 24px;border-left:4px solid {color}">
            <div style="font-size:13px;color:#888;margin-bottom:6px">{label}</div>
            <div style="font-size:28px;font-weight:700;color:{color}">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

kpi_card(k1, "Overall Pass Rate", f"{pass_rate:.1f}%", rate_color)
kpi_card(k2, "Total Trials", str(total_trials))
kpi_card(k3, "Avg Placement Error", f"{avg_error:.2f} mm")
kpi_card(k4, "Avg Cycle Time", f"{avg_time:.2f} s")

st.write("")

# ── Section 2 — Failure Analysis ─────────────────────────────────────────────
st.subheader("Failure Analysis")
c1, c2 = st.columns(2)

with c1:
    failed = df[df["success"] == False]
    if failed.empty:
        st.info("No failures in this run.")
    else:
        tag_counts = failed["failure_tag"].value_counts().reset_index()
        tag_counts.columns = ["failure_tag", "count"]
        fig_pie = px.pie(
            tag_counts,
            names="failure_tag",
            values="count",
            title="Failure Distribution",
            color_discrete_sequence=px.colors.qualitative.Bold,
            template=DARK,
            hole=0.4,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=50, b=10, l=10, r=10))
        st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    obj_pass = (
        df.groupby("object")["success"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"success": "pass_rate"})
    )
    fig_obj = px.bar(
        obj_pass,
        x="object",
        y="pass_rate",
        title="Pass Rate by Object Type",
        labels={"pass_rate": "Pass Rate (%)", "object": "Object"},
        color="pass_rate",
        color_continuous_scale=[[0, "#e74c3c"], [0.5, "#f39c12"], [1, "#2ecc71"]],
        range_color=[0, 100],
        template=DARK,
        text=obj_pass["pass_rate"].map(lambda x: f"{x:.0f}%"),
    )
    fig_obj.update_traces(textposition="outside")
    fig_obj.update_layout(
        coloraxis_showscale=False,
        yaxis_range=[0, 110],
        margin=dict(t=50, b=10, l=10, r=10),
    )
    st.plotly_chart(fig_obj, use_container_width=True)

# ── Section 3 — Scenario Deep Dive ───────────────────────────────────────────
st.subheader("Scenario Deep Dive")
c3, c4 = st.columns(2)

with c3:
    scen_pass = (
        df.groupby("scenario_id")["success"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"success": "pass_rate"})
        .sort_values("scenario_id")
    )
    colors = ["#2ecc71" if v >= 70 else "#e74c3c" for v in scen_pass["pass_rate"]]
    fig_scen = go.Figure(
        go.Bar(
            x=scen_pass["scenario_id"],
            y=scen_pass["pass_rate"],
            marker_color=colors,
            text=[f"{v:.0f}%" for v in scen_pass["pass_rate"]],
            textposition="outside",
        )
    )
    fig_scen.update_layout(
        title="Pass Rate by Scenario",
        xaxis_title="Scenario",
        yaxis_title="Pass Rate (%)",
        yaxis_range=[0, 110],
        template=DARK,
        margin=dict(t=50, b=10, l=10, r=10),
    )
    st.plotly_chart(fig_scen, use_container_width=True)

with c4:
    tol_pass = (
        df.groupby("placement_tolerance_mm")["success"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"success": "pass_rate"})
    )
    tol_pass["label"] = tol_pass["placement_tolerance_mm"].map(
        lambda x: f"Easy ({x:.0f}mm)" if x >= 20 else f"Hard ({x:.0f}mm)"
    )
    fig_tol = px.bar(
        tol_pass,
        x="label",
        y="pass_rate",
        title="Pass Rate by Tolerance",
        labels={"pass_rate": "Pass Rate (%)", "label": "Tolerance"},
        color="pass_rate",
        color_continuous_scale=[[0, "#e74c3c"], [0.5, "#f39c12"], [1, "#2ecc71"]],
        range_color=[0, 100],
        template=DARK,
        text=tol_pass["pass_rate"].map(lambda x: f"{x:.0f}%"),
    )
    fig_tol.update_traces(textposition="outside")
    fig_tol.update_layout(
        coloraxis_showscale=False,
        yaxis_range=[0, 110],
        margin=dict(t=50, b=10, l=10, r=10),
    )
    st.plotly_chart(fig_tol, use_container_width=True)

# ── Section 4 — Performance Distribution ─────────────────────────────────────
st.subheader("Performance Distribution")
c5, c6 = st.columns(2)

with c5:
    tolerance_val = df["placement_tolerance_mm"].median()
    fig_hist = px.histogram(
        df,
        x="placement_error_mm",
        nbins=20,
        title="Placement Error Distribution",
        labels={"placement_error_mm": "Placement Error (mm)"},
        color_discrete_sequence=["#5b8fff"],
        template=DARK,
    )
    fig_hist.add_vline(
        x=tolerance_val,
        line_dash="dash",
        line_color="#f39c12",
        annotation_text=f"Tolerance ({tolerance_val:.0f}mm)",
        annotation_position="top right",
        annotation_font_color="#f39c12",
    )
    fig_hist.update_layout(margin=dict(t=50, b=10, l=10, r=10))
    st.plotly_chart(fig_hist, use_container_width=True)

with c6:
    df_scatter = df.copy()
    df_scatter["result"] = df_scatter["success"].map({True: "Pass", False: "Fail"})
    fig_scatter = px.scatter(
        df_scatter,
        x="cycle_time_s",
        y="placement_error_mm",
        color="result",
        color_discrete_map={"Pass": "#2ecc71", "Fail": "#e74c3c"},
        title="Cycle Time vs Placement Error",
        labels={
            "cycle_time_s": "Cycle Time (s)",
            "placement_error_mm": "Placement Error (mm)",
        },
        hover_data=["scenario_id", "object", "failure_tag"],
        template=DARK,
    )
    fig_scatter.update_traces(marker=dict(size=8, opacity=0.8))
    fig_scatter.update_layout(margin=dict(t=50, b=10, l=10, r=10))
    st.plotly_chart(fig_scatter, use_container_width=True)

# ── Section 5 — Raw Results Table ────────────────────────────────────────────
st.subheader("Raw Results")

def color_success(val):
    if val is True:
        return "background-color: #1a4a2e; color: #2ecc71"
    elif val is False:
        return "background-color: #4a1a1a; color: #e74c3c"
    return ""

styled = df.style.map(color_success, subset=["success"])
st.dataframe(styled, use_container_width=True, height=400)

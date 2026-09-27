"""Project Deep-Dive — PRD §7/Phase 6 screen 3.

Predicted vs. approved cost with an uncertainty band, risk trajectory over
time, a SHAP waterfall for the current snapshot, and a delay-reason timeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from paimana import config
from paimana.app.common import (
    load_projects,
    load_quantile_predictions,
    load_risk_scores,
    load_shap_values,
    render_synthetic_banner,
)

st.set_page_config(page_title="PARIKSHAN — Project Deep-Dive", page_icon="🔎", layout="wide")

st.title("🔎 Project Deep-Dive")
render_synthetic_banner()

risk_df = load_risk_scores()
projects_df = load_projects()
quantile_df = load_quantile_predictions()
shap_df = load_shap_values()

project_options = projects_df[["project_id", "project_name"]].sort_values("project_id")
selected_id = st.selectbox(
    "Select a project",
    options=project_options["project_id"].tolist(),
    format_func=lambda pid: f"{pid} — {project_options.set_index('project_id').loc[pid, 'project_name']}",
)

project_static = projects_df[projects_df["project_id"] == selected_id].iloc[0]
project_risk = risk_df[risk_df["project_id"] == selected_id].sort_values("as_of_date")
project_quantiles = quantile_df[quantile_df["project_id"] == selected_id].sort_values("as_of_date").copy()

# Light display-only smoothing: unconstrained gradient-boosted quantile
# regression has no monotonicity guarantee across neighbouring quarters,
# and can occasionally produce an isolated single-quarter spike (verified
# directly against the cached data: one quarter's p90 at ~4x its
# neighbours' value, then back to normal) — real model output, not a
# plotting bug, but showing it raw looks like a glitch and would undermine
# trust in an otherwise sound chart. Smoothing is applied ONLY here, for
# display; the underlying quantile_predictions.parquet is untouched.
_band_cols = ["predicted_final_cost_p10_cr", "predicted_final_cost_p50_cr", "predicted_final_cost_p90_cr"]
if len(project_quantiles) >= 3:
    project_quantiles[_band_cols] = (
        project_quantiles[_band_cols].rolling(window=3, center=True, min_periods=1).median()
    )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Sector", project_static["sector"])
col2.metric("Approved cost", f"₹{project_static['original_cost_cr']:,.0f} cr")
col3.metric("Status", "Ongoing" if project_static["is_censored"] else "Completed")
latest_band = project_risk.iloc[-1]["risk_band"] if len(project_risk) else "—"
col4.metric("Current risk band", latest_band)

st.divider()

# --------------------------------------------------------------------------
# Predicted vs. approved cost with an uncertainty band
# --------------------------------------------------------------------------
st.subheader("Predicted final cost vs. approved cost (10th-90th percentile band)")
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=project_quantiles["as_of_date"], y=project_quantiles["predicted_final_cost_p90_cr"],
        line={"width": 0}, showlegend=False, hoverinfo="skip",
    )
)
fig.add_trace(
    go.Scatter(
        x=project_quantiles["as_of_date"], y=project_quantiles["predicted_final_cost_p10_cr"],
        fill="tonexty", fillcolor="rgba(66,133,244,0.2)", line={"width": 0},
        name="10th-90th percentile band",
    )
)
fig.add_trace(
    go.Scatter(
        x=project_quantiles["as_of_date"], y=project_quantiles["predicted_final_cost_p50_cr"],
        line={"color": "#4285f4"}, name="Predicted final cost (median)",
    )
)
fig.add_hline(
    y=project_static["original_cost_cr"], line_dash="dash", line_color="#2e7d32",
    annotation_text="Approved cost",
)
fig.update_layout(margin={"t": 10, "b": 10, "l": 10, "r": 10}, yaxis_title="Rs crore")
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Quantile predictions come from an XGBoost quantile regressor (PRD §6.3); interval coverage "
    "was measured (not assumed) in Phase 4 at ~70-71% against an 80% target — see BAKEOFF.md. "
    "The band is lightly smoothed (3-quarter rolling median) for display only — unconstrained "
    "quantile regression has no monotonicity guarantee across neighbouring quarters and can "
    "occasionally spike for a single one."
)

st.divider()

# --------------------------------------------------------------------------
# Risk trajectory
# --------------------------------------------------------------------------
st.subheader("Risk score trajectory")
fig = px.line(project_risk, x="as_of_date", y="risk_score", markers=True)
fig.add_hrect(y0=0, y1=config.RISK_BAND_GREEN_MAX, fillcolor="#2e7d32", opacity=0.08, line_width=0)
fig.add_hrect(
    y0=config.RISK_BAND_GREEN_MAX, y1=config.RISK_BAND_AMBER_MAX, fillcolor="#f9a825", opacity=0.08,
    line_width=0,
)
fig.add_hrect(y0=config.RISK_BAND_AMBER_MAX, y1=100, fillcolor="#c62828", opacity=0.08, line_width=0)
fig.update_layout(margin={"t": 10, "b": 10, "l": 10, "r": 10}, yaxis_range=[0, 100], yaxis_title="Risk score")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------
# SHAP waterfall (current snapshot only — see Phase 4/5 scope notes)
# --------------------------------------------------------------------------
st.subheader("Why this project's current risk score — top drivers")
project_shap = shap_df[shap_df["project_id"] == selected_id]
if project_shap.empty:
    st.info("No cached SHAP explanation for this project (it may not be in the y_severe model's scope).")
else:
    feature_cols = [c for c in shap_df.columns if c not in ("project_id", "as_of_date")]
    row = project_shap.iloc[0][feature_cols].astype(float)
    top = row.reindex(row.abs().sort_values(ascending=False).index).head(10)
    top.index = [i.replace("num__", "").replace("cat__", "") for i in top.index]
    colors = ["#c62828" if v > 0 else "#2e7d32" for v in top.values]
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=colors))
    fig.update_layout(
        margin={"t": 10, "b": 10, "l": 10, "r": 10},
        xaxis_title="SHAP contribution to severe-overrun risk (as of latest snapshot)",
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Red bars push risk up; green bars push risk down, based on the project's latest snapshot.")

st.divider()

# --------------------------------------------------------------------------
# Delay-reason timeline
# --------------------------------------------------------------------------
st.subheader("Delay-reason timeline")
reason_cols = [c for c in project_risk.columns if c.startswith("reason_")]
if not reason_cols or project_risk.empty:
    st.info("No delay-reason data available for this project.")
else:
    timeline = project_risk.set_index("as_of_date")[reason_cols].astype(int)
    timeline.columns = [c.replace("reason_", "") for c in timeline.columns]
    active_cols = timeline.columns[timeline.sum() > 0]
    if len(active_cols) == 0:
        st.success("No delay reasons were ever recorded as active for this project.")
    else:
        fig = px.imshow(
            timeline[active_cols].T,
            aspect="auto",
            color_continuous_scale=["white", "#c62828"],
            labels={"x": "As of date", "y": "Delay reason", "color": "Active"},
        )
        fig.update_layout(margin={"t": 10, "b": 10, "l": 10, "r": 10})
        st.plotly_chart(fig, use_container_width=True)

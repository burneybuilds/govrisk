"""Portfolio Overview — PRD §7/Phase 6 screen 1.

KPI tiles, sector risk heatmap, risk-band distribution, state breakdown —
the 30-second view of the whole 1,981-project portfolio's current state.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from paimana.app.common import (
    latest_snapshot_per_project,
    load_projects,
    load_risk_scores,
    render_synthetic_banner,
    risk_band_color,
)

st.set_page_config(page_title="PARIKSHAN — Portfolio Overview", page_icon="📊", layout="wide")

st.title("📊 PARIKSHAN — Portfolio Overview")
render_synthetic_banner()

risk_df = load_risk_scores()
projects_df = load_projects()
latest = latest_snapshot_per_project(risk_df).merge(
    projects_df[["project_id", "is_censored"]], on="project_id", how="left"
)

# --------------------------------------------------------------------------
# KPI tiles
# --------------------------------------------------------------------------
n_projects = latest["project_id"].nunique()
n_ongoing = int((latest["is_censored"] == True).sum())  # noqa: E712
total_outlay_cr = projects_df["original_cost_cr"].sum()
n_at_risk = (latest["risk_band"] != "Green").sum()
avg_predicted_overrun = latest["pred_cost_overrun_pct"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Projects tracked", f"{n_projects:,}", f"{n_ongoing:,} currently ongoing")
col2.metric("Total approved outlay", f"₹{total_outlay_cr / 1000:,.1f}k cr")
col3.metric("Projects at risk (Amber/Red)", f"{n_at_risk:,}", f"{n_at_risk / n_projects:.0%} of portfolio")
col4.metric("Avg. predicted cost overrun", f"{avg_predicted_overrun:.1f}%")

st.divider()

# --------------------------------------------------------------------------
# Risk-band distribution + sector heatmap
# --------------------------------------------------------------------------
left, right = st.columns([1, 2])

with left:
    st.subheader("Risk-band distribution")
    band_counts = latest["risk_band"].value_counts().reindex(["Green", "Amber", "Red"]).fillna(0)
    fig = px.pie(
        values=band_counts.values,
        names=band_counts.index,
        color=band_counts.index,
        color_discrete_map={b: risk_band_color(b) for b in ("Green", "Amber", "Red")},
        hole=0.45,
    )
    fig.update_traces(textinfo="value+percent")
    fig.update_layout(showlegend=True, margin={"t": 10, "b": 10, "l": 10, "r": 10})
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Mean risk score by sector")
    sector_risk = (
        latest.groupby("sector")["risk_score"].mean().sort_values(ascending=False).reset_index()
    )
    fig = px.bar(
        sector_risk,
        x="risk_score",
        y="sector",
        orientation="h",
        color="risk_score",
        color_continuous_scale=["#2e7d32", "#f9a825", "#c62828"],
        range_color=[0, 100],
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}, margin={"t": 10, "b": 10, "l": 10, "r": 10}
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------
# State breakdown
# --------------------------------------------------------------------------
st.subheader("Projects at risk by state")
state_summary = (
    latest.groupby("state")
    .agg(n_projects=("project_id", "count"), n_at_risk=("risk_band", lambda s: (s != "Green").sum()))
    .assign(pct_at_risk=lambda d: d["n_at_risk"] / d["n_projects"])
    .sort_values("n_at_risk", ascending=False)
    .head(20)
    .reset_index()
)
fig = px.bar(
    state_summary,
    x="state",
    y=["n_at_risk", "n_projects"],
    barmode="overlay",
    labels={"value": "Projects", "variable": ""},
)
fig.update_layout(height=480, margin={"t": 10, "b": 140, "l": 10, "r": 10}, xaxis_tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Use the sidebar to navigate to the Early Warning Centre, Project Deep-Dive, "
    "Model Lab, or the LLM Assistant."
)

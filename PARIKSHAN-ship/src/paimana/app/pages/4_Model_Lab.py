"""Model Lab — PRD §7/Phase 6 screen 4.

The bake-off table, calibration curves, PR curves, Precision@K, and the
full per-family metrics — the rigour screen.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from paimana.app.common import (
    load_calibration_curves,
    load_comparison,
    load_pr_curves,
    load_precision_at_k_curves,
    render_synthetic_banner,
)

st.set_page_config(page_title="PARIKSHAN — Model Lab", page_icon="🧪", layout="wide")

st.title("🧪 Model Lab — ML vs. Conventional Statistics")
render_synthetic_banner()

comparison = load_comparison()
targets = comparison["targets"]

st.info(comparison["headline"], icon="📌")

# --------------------------------------------------------------------------
# Bake-off table
# --------------------------------------------------------------------------
st.subheader("Bake-off: conventional baseline vs. best ML model")
rows = []
for target, entry in targets.items():
    is_reg = entry["task"] == "regression"
    conv_score = entry["conventional_r2"] if is_reg else entry["conventional_pr_auc"]
    ml_score = entry["ml_r2"] if is_reg else entry["ml_pr_auc"]
    ci = entry["bootstrap"]
    verdict = (
        "ML wins" if ci["ci_excludes_zero"] and ci["mean_diff"] > 0
        else "Conventional wins" if ci["ci_excludes_zero"]
        else "No significant difference"
    )
    rows.append(
        {
            "Target": target,
            "Task": entry["task"],
            "Metric": "R²" if is_reg else "PR-AUC",
            "Conventional": entry["conventional_model"],
            "Conv. score": round(conv_score, 4),
            "ML model": entry["ml_model"],
            "ML score": round(ml_score, 4),
            "Bootstrap 95% CI (ML - conv)": f"[{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}]",
            "Verdict": verdict,
        }
    )
bakeoff_table = pd.DataFrame(rows)
st.dataframe(bakeoff_table, use_container_width=True, hide_index=True)

st.divider()

# --------------------------------------------------------------------------
# Full per-family metrics
# --------------------------------------------------------------------------
st.subheader("Full per-family metrics")
target_choice = st.selectbox("Target", options=list(targets.keys()))
entry = targets[target_choice]
is_reg = entry["task"] == "regression"
key_metric = "r2" if is_reg else "pr_auc"
family_metrics = pd.DataFrame(entry["all_ml_family_metrics"]).T
st.dataframe(family_metrics[[key_metric]].round(4), use_container_width=True)

if "delong" in entry:
    d = entry["delong"]
    st.caption(
        f"DeLong test (ROC-AUC): ML AUC={d['auc_a']:.4f} vs. conventional AUC={d['auc_b']:.4f}, "
        f"z={d['z_statistic']:.2f}, p={d['p_value']:.4g}"
    )

st.divider()

# --------------------------------------------------------------------------
# Calibration curves
# --------------------------------------------------------------------------
st.subheader("Calibration (reliability curves)")
calib = load_calibration_curves()
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines", line={"dash": "dash", "color": "gray"},
        name="Perfect calibration",
    )
)
for key, curve in calib.items():
    fig.add_trace(go.Scatter(x=curve["predicted"], y=curve["observed"], mode="lines+markers", name=key))
fig.update_layout(
    xaxis_title="Mean predicted probability", yaxis_title="Observed frequency",
    margin={"t": 10, "b": 10, "l": 10, "r": 10},
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------
# PR curves
# --------------------------------------------------------------------------
st.subheader("Precision-Recall curves (classification targets, OOF)")
pr_curves = load_pr_curves()
fig = go.Figure()
for target, curve in pr_curves.items():
    fig.add_trace(go.Scatter(x=curve["recall"], y=curve["precision"], mode="lines", name=target))
fig.update_layout(
    xaxis_title="Recall", yaxis_title="Precision", margin={"t": 10, "b": 10, "l": 10, "r": 10}
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------
# Precision@K
# --------------------------------------------------------------------------
st.subheader("Precision@K — the alert-queue metric")
st.caption(
    "MoSPI's real constraint is reviewer bandwidth, not information: 'of the top K projects we'd "
    "flag, how many actually overrun?' matters more than a blended AUC (PRD §1.3)."
)
pak_curves = load_precision_at_k_curves()
fig = go.Figure()
for target, curve in pak_curves.items():
    fig.add_trace(go.Scatter(x=curve["k"], y=curve["precision"], mode="lines+markers", name=target))
    fig.add_hline(y=curve["base_rate"], line_dash="dot", opacity=0.3)
fig.update_layout(
    xaxis_title="K (top-K ranked by predicted probability)", yaxis_title="Precision@K",
    margin={"t": 10, "b": 10, "l": 10, "r": 10},
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Conventional-baseline model cards")
st.caption("Full statsmodels/lifelines model cards from Phase 3 are in `artifacts/metrics/cards/`.")

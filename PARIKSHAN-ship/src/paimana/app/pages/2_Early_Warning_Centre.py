"""Early Warning Centre — PRD §7/Phase 6 screen 2.

The sortable/filterable alert queue: severity, triggered rules, risk
score, recommended action, and (where cached) SHAP reason codes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd
import streamlit as st

from paimana.app.common import load_alerts, render_synthetic_banner, severity_color

st.set_page_config(page_title="PARIKSHAN — Early Warning Centre", page_icon="🚨", layout="wide")


def _has_reason_codes(codes) -> bool:
    """True if `codes` is a non-empty sequence of reason-code dicts.

    NOT `isinstance(codes, list)`: pyarrow round-trips a parquet
    list-of-struct column back as `numpy.ndarray`, not a native Python
    `list` — an `isinstance(c, list)` check silently matches nothing for
    every real value once read back from disk (found by actually clicking
    through the running app, not assumed). `len()` works identically on
    both, and `None` (the no-codes case) raises TypeError, caught below.
    """
    if codes is None:
        return False
    try:
        return len(codes) > 0
    except TypeError:
        return False

st.title("🚨 Early Warning Centre")
render_synthetic_banner()

alerts_df = load_alerts()

# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
show_latest_only = st.checkbox(
    "Show only each project's most recent alert (the current review queue)", value=True
)
col1, col2 = st.columns(2)
severities = col1.multiselect(
    "Severity", options=["Critical", "High", "Medium"], default=["Critical", "High", "Medium"]
)
sectors = col2.multiselect(
    "Sector", options=sorted(alerts_df["sector"].dropna().unique()), default=[]
)

view = alerts_df[alerts_df["severity"].isin(severities)]
if sectors:
    view = view[view["sector"].isin(sectors)]
if show_latest_only:
    view = view.sort_values("as_of_date").groupby("project_id", as_index=False).last()

view = view.sort_values(
    "severity", key=lambda s: s.map({"Critical": 0, "High": 1, "Medium": 2})
).reset_index(drop=True)

st.caption(f"{len(view):,} alert(s) matching the current filters (of {len(alerts_df):,} total on record).")

# --------------------------------------------------------------------------
# Severity chip summary
# --------------------------------------------------------------------------
chip_cols = st.columns(3)
for col, sev in zip(chip_cols, ["Critical", "High", "Medium"], strict=True):
    count = (view["severity"] == sev).sum()
    col.markdown(
        f"<div style='background-color:{severity_color(sev)}22;border:1px solid {severity_color(sev)};"
        f"border-radius:8px;padding:10px;text-align:center;'>"
        f"<span style='color:{severity_color(sev)};font-weight:700;font-size:1.4em'>{count}</span><br>"
        f"<span style='color:{severity_color(sev)};'>{sev}</span></div>",
        unsafe_allow_html=True,
    )

st.divider()

# --------------------------------------------------------------------------
# Alert table
# --------------------------------------------------------------------------
display_df = view.copy()
display_df["triggered_rules"] = display_df["triggered_rules"].apply(
    lambda rules: ", ".join(rules) if isinstance(rules, list) else rules
)
display_df["risk_score"] = display_df["risk_score"].round(1)
display_df["has_reason_codes"] = display_df["reason_codes"].apply(_has_reason_codes)

table_cols = [
    "as_of_date", "project_id", "project_name", "sector", "severity",
    "triggered_rules", "risk_score", "recommended_action", "has_reason_codes",
]
st.dataframe(
    display_df[table_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "risk_score": st.column_config.ProgressColumn(
            "Risk score", min_value=0, max_value=100, format="%.0f"
        ),
        "has_reason_codes": st.column_config.CheckboxColumn("SHAP explanation available"),
        "as_of_date": st.column_config.DateColumn("As of"),
    },
)

st.download_button(
    "⬇️ Export filtered alerts as CSV",
    data=display_df[table_cols].to_csv(index=False).encode("utf-8"),
    file_name="parikshan_alerts_export.csv",
    mime="text/csv",
)

st.divider()

# --------------------------------------------------------------------------
# Reason-code detail for a selected alert
# --------------------------------------------------------------------------
st.subheader("Reason codes for a selected alert")
options_with_codes = view[view["reason_codes"].apply(_has_reason_codes)]
if options_with_codes.empty:
    st.info(
        "None of the currently filtered alerts have a cached SHAP explanation — reason codes are "
        "only available for a project's true latest snapshot (see PRD §5, Phase 5 Handoff for why)."
    )
else:
    selected_id = st.selectbox(
        "Project", options=options_with_codes["project_id"].tolist(), format_func=lambda pid: pid
    )
    row = options_with_codes[options_with_codes["project_id"] == selected_id].iloc[0]
    # list(...): pd.DataFrame() does NOT expand a numpy.ndarray-of-dicts into
    # columns the way it does a native list-of-dicts (it instead makes one
    # column of raw dict objects) — the same ndarray-vs-list round-trip
    # quirk as `_has_reason_codes` above, verified directly before fixing.
    codes_df = pd.DataFrame(list(row["reason_codes"]))
    codes_df["feature"] = codes_df["feature"].str.replace(r"^(num__|cat__)", "", regex=True)
    codes_df = codes_df.rename(columns={"feature": "Driver", "shap_value": "SHAP contribution"})
    st.dataframe(codes_df, hide_index=True, use_container_width=True)

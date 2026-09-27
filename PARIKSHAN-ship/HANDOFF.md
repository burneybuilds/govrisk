# PARIKSHAN — Phase Handoff Log

---

## PHASE 7 — LLM Assistant & Demo Hardening
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~5h (over the ~4h budget — the Ollama/torch DLL investigation and the live-UI-discovered anti-hallucination gap both took real, unplanned time)

**This is the final phase of the PRD's 7-phase plan.** PARIKSHAN is now complete end-to-end: all 7 phases built, verified, and documented. Phase 7 was explicitly droppable (Phases 1-6 are already a complete, demo-able submission) — it shipped anyway, including a real offline model.

### What was built
- **Ollama installed and `qwen2.5:7b-instruct` (Apache-2.0, 4.7GB) pulled**, with the user's explicit permission (asked via `AskUserQuestion` when Ollama was found missing; user chose "Install Ollama for me"). Confirmed sufficient hardware first (85.5GB RAM, 16 cores, NVIDIA T1200 4GB VRAM — plenty for a 7B model on CPU).
- `src/paimana/assistant/tools.py` — 10 whitelisted pandas tools (`portfolio_summary`, `sector_risk_summary`, `state_risk_summary`, `top_risk_projects`, `project_detail`, `alert_digest`, `compare_sectors`, `model_bakeoff_summary`, `backtest_summary`, `delay_reason_breakdown`), each reading only already-cached artifacts, each raising `ValueError` on bad input, registered in `TOOL_REGISTRY`.
- `src/paimana/assistant/retriever.py` — two-layer intent routing: fast keyword/regex rules first, MiniLM (`all-MiniLM-L6-v2`) embedding cosine-similarity as the fallback, plus a third capability — brute-force numpy cosine search over ~1,981 precomputed project-narrative embeddings (PRD §3.1's explicit "no vector DB" — see Phase 1's ChromaDB rejection) to resolve a project named by description rather than by ID.
- `src/paimana/assistant/llm.py` — the Ollama client (`qwen2.5:7b-instruct`, 90s timeout to absorb a cold model load), a strict system prompt ("narrate only the supplied numbers, never invent or compute"), the deterministic Jinja fallback template, and `verify_numeric_fidelity` — an automated checker that every number in an answer traces to the tool's verified output (with explicit, tested allowances for percentage conversion, absolute values, digits embedded in identifiers/dict keys, list-truncation arithmetic, and free-form ordinal list markers).
- `scripts/run_assistant_index.py` — precomputes the 1,981 project narratives + MiniLM embeddings once, offline.
- `scripts/run_assistant_eval.py` — runs the 8 golden questions through the REAL Ollama path (not the fallback) and reports pass/fail per question.
- `scripts/run_offline_check.py` — patches `socket.socket.connect`/`connect_ex` to block any non-loopback connection, then exercises the core pipeline (data load, risk artifacts, assistant tools, rule routing, deterministic narration) to prove zero outbound network calls; verified the guard itself actually blocks a real connection attempt before trusting a "PASS" from it.
- `src/paimana/app/pages/5_Assistant.py` — the real chat UI, replacing Phase 6's placeholder: example-question buttons, chat history, source label (Ollama vs. fallback), routing-method label, raw verified JSON in an expander, and a new "⚠️ answer rejected" notice (see the anti-hallucination gap below).
- `tests/test_assistant_tools.py` (35 tests) — every tool's structure/correctness against real cached data, plus rule-routing coverage.
- `tests/test_golden_questions.py` (22 tests) — the 8 canonical questions × routing-correctness + numeric-fidelity, plus 5 direct unit tests of `verify_numeric_fidelity` itself.
- `docs/DEMO_SCRIPT.md` — a beat-by-beat 5-minute demo run sheet with real numbers pulled from cached artifacts.
- `README.md` — full rewrite: real headline results, an expanded, verified "Honest limitations" section, and quickstart steps that actually match what this build needed (including the torch CPU-only-build workaround).
- `LICENSES.md` — added the `torch` row with its CPU-only-build caveat.

### DoD verification (commands actually run)
```
$ ollama list
NAME                   ID              SIZE      MODIFIED
qwen2.5:7b-instruct    845dbda0ea48    4.7 GB    ~1h ago

$ python -m pytest tests/test_assistant_tools.py tests/test_golden_questions.py -q
.......................................................  [100%]
57 passed in 15.62s   (66 passed together with test_app_smoke.py's 9)

$ python scripts/run_assistant_eval.py     # REAL Ollama, not fallback
[PASS] x8 — 8/8 passed, 8/8 answered by live Ollama, 0 fell back

$ python scripts/run_offline_check.py
PASS: core pipeline ... completed with zero outbound network connections.
(guard verified separately to actually block a real connect() to 8.8.8.8:53
 before trusting this PASS — see Key decisions below)

$ ruff check src/ tests/ scripts/
All checks passed!

$ python -m pytest -q          # full repo suite
236 passed, 915 warnings in 755.47s (0:12:35)
```
- [x] `ollama list` shows `qwen2.5:7b-instruct`
- [x] `test_assistant_tools.py` + `test_golden_questions.py` green (57/57)
- [x] `run_assistant_eval.py` — **8/8 golden questions pass against the live model**, not just the fallback template
- [x] `run_offline_check.py` passes, and the network guard was proven to actually block a real socket connect, not silently no-op
- [x] ruff clean across `src/`, `tests/`, `scripts/`
- [x] **Full-suite `pytest -q`: 236/236 passed** — confirmed clean on a genuine re-run after both DLL-conflict-catching fixes landed (the suite had failed at 234/236 mid-phase on the exact bug documented below; re-ran to a clean 236/236 after fixing it, not assumed fixed from the targeted 6/6 re-run alone).

### Visual check (mandatory, performed live via the browser tool)
- Loaded the dashboard fresh, navigated **Home → Early Warning Centre → Model Lab → Assistant** (the exact order `DEMO_SCRIPT.md` prescribes) in a single browser session, so pandas/numpy/sklearn/xgboost were already loaded in-process before Assistant's torch preload ran — this is the precise ordering that had caused a live crash (see below) and confirming it *doesn't* crash post-fix was the actual point of this check, not just loading Assistant in isolation.
- Asked the live assistant real questions ("How many projects are at risk?", "What is the riskiest sector?", "How early would we have caught eventual severe overruns?") and got correctly-grounded live Ollama answers each time.
- **Killed Ollama mid-session** (`Stop-Process` on both `ollama` processes, confirmed unreachable via a failed `curl` to `localhost:11434`) and asked another question — the UI seamlessly fell back to the deterministic template, labelled "📋 Deterministic fallback", with the exact same real numbers (237 eventually-severe projects, 206 flagged, 18-quarter median lead time, 81.43% recall) verified earlier against the live-Ollama answer to the same question.
- Restarted Ollama afterward to leave the machine in the state it was found.

### Key decisions & deviations from PRD
1. **`verify_numeric_fidelity` is now wired into the live `answer_question()` path, not just tests** — see the anti-hallucination gap below; this is the single most consequential decision of the phase.
2. **The offline-check network guard was empirically proven to work**, not assumed: before trusting `run_offline_check.py`'s "PASS", a separate throwaway script confirmed the same guard genuinely raises `OutboundConnectionError` when something actually tries to reach `8.8.8.8:53` — a check that passes vacuously (nothing in the exercised code path happens to touch the network) would otherwise be indistinguishable from a check that works.
3. **The offline check does not exercise the live Ollama call** — Ollama itself is a loopback (`127.0.0.1`) HTTP call, which the guard deliberately allows (the "fully offline" constraint is about not depending on an external/hosted service, not literally zero sockets). `run_offline_check.py` exercises only the fallback-template path, which is the one guaranteed to work with genuinely zero network access.
4. **`_ordinal_markers` and `_truncation_counts` were added to `verify_numeric_fidelity`** after the golden-question suite's fallback-path tests failed on numbers like "17.0" (from the fallback template's own "(+17 more)" truncation text) and "2.0"/"4.0" (from a live LLM's own numbered-list formatting, "1. ... 2. ... 3. ..."). Both are legitimate artifacts of *rendering*, not hallucinations — confirmed by printing the actual rendered text in each case before writing any fix, per this project's standing "verify before fixing" discipline.

### Two real bugs found only by running the actual thing — not assumed fixed after tests passed
1. **The exact same DLL-conflict bug, twice, in two different files.** `retriever.py`'s top-of-file torch preload used `except ImportError: pass` — but the real failure on this machine is `OSError: [WinError 1114] ... c10.dll`, which that clause does not catch. This was invisible running `test_assistant_tools.py`/`test_golden_questions.py` in isolation (Python's import order there never hit the conflict), and only surfaced running the **full** `pytest -q` suite, where an earlier-collected test module had already imported pandas by the time `retriever.py` was reached — crashing collection of two test files outright. Fixed by broadening to `except Exception`. The exact same bug, independently, was also present at the top of `pages/5_Assistant.py` — found by the mandatory live-browser check: navigating straight to the Assistant page after visiting other dashboard pages (which had already loaded pandas) produced a live, user-visible `OSError` traceback in the browser, directly contradicting that file's own docstring claim that "this screen cannot hard-fail during a demo." Fixed identically. **Lesson for future work on this file:** any bare `except ImportError` guarding a torch preload on this machine is suspect — the real failure mode is `OSError`, and only a full, realistic exercise (full test suite; a live multi-page click-through) reveals it, not an isolated single-file test run.
2. **A genuine, reproducible anti-hallucination gap: `verify_numeric_fidelity` existed and was unit-tested but was never actually called on the live path.** Live-clicking through the demo flow (Home → ... → Assistant), asking "What is the riskiest sector?" produced a real Qwen2.5-7B answer stating "There are a total of 1,426 projects across all sectors, with 299 projects currently at risk" — **neither number appears anywhere in the tool's verified output** (confirmed directly: `verify_numeric_fidelity` correctly flags `[1426.0, 299.0]` as unverified when run against the actual captured text). `scripts/run_assistant_eval.py`'s one-sample-per-question live run had, by chance, not hit this on its earlier pass — a reminder that sampling an LLM's output once is not the same guarantee as checking every answer. Fixed by wiring `verify_numeric_fidelity` into `answer_question()` itself: every live Ollama narration is now checked before being shown, and a failed check silently substitutes the verified deterministic template (`AssistantResponse.ollama_answer_rejected = True`), surfaced in the UI as "⚠️ The local model's answer was rejected because it stated a number that couldn't be verified... showing the deterministic template instead." Proven end-to-end with a mocked Ollama response replaying the exact captured hallucination text — confirms `source="fallback"`, `ollama_answer_rejected=True`, and the correct real answer rendered.
   - **Separately, and not fixed** (numeric fidelity is not the same guarantee as full correctness): the model has a reproducible tendency to name "Shipping & Ports" (mean risk score 35.7) as the "riskiest sector" when "Civil Aviation" (35.8) actually ranks higher — every individual number it states is real and traceable, so `verify_numeric_fidelity` correctly passes these answers, but the *ranking claim* is wrong. This is a known, disclosed limitation (see README), not a bug the current architecture is designed to catch — catching it would require a second, claim-level verifier, out of scope for this phase.

### Known issues / debt carried forward
- Same PRD Open Item O-1 (unverified calibration anchors) — unaffected by this phase.
- The model's ranking/reasoning errors (see above) are not caught by numeric fidelity checking — disclosed as an honest limitation, not silently hidden.
- `run_assistant_index.py` must be re-run if the underlying project data is ever regenerated (its narratives and embeddings are a one-time cache, same category as Phase 4/5's precomputed artifacts).
- The embedding/MiniLM layer's reliability on this specific Windows machine is now more robust (both known crash sites fixed) but still fundamentally dependent on a fragile native DLL interaction between torch and numpy/pandas; a different machine may not hit this at all, or could hit it in a third place not yet found — the mitigation is architectural (broad exception catching + graceful degradation everywhere `torch` is preloaded), not a permanent fix of the underlying DLL conflict.

### ⏭️ NEXT AGENT / FINAL WRAP-UP STARTS HERE
**All 7 PRD phases are now complete, verified, and committed.** There is no Phase 8 — this was the last phase in the PRD's plan. Any further work is polish, not a new phase. If picking this project back up:
- `git log` for the Phase 7 commit to see exactly what shipped.
- Re-verify preconditions per Rule 3 rather than trusting this report blindly: `ollama list`, `python -m pytest -q`, `ruff check src/ tests/ scripts/`.
- Read the two "real bugs found only by running the actual thing" above before touching `retriever.py`, `pages/5_Assistant.py`, or `llm.py`'s `answer_question()` — both fixes are load-bearing, not incidental.

## PHASE 6 — Streamlit Dashboard — MVP CUT LINE
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~4h (under the ~5h budget)

**This is the MVP cut line (PRD §1.5).** PARIKSHAN is now a complete, demo-able, submittable product. Phase 7 (the offline LLM assistant) is a bonus layered on a working system, not a dependency of it.

### What was built
- `scripts/run_dashboard_data.py` — precomputes what Phases 4-5 never cached: quantile predictions (p10/p50/p90) for the full 51,591-row panel (`data/processed/quantile_predictions.parquet`), and PR-curve/Precision@K-vs-K data for the 3 classification targets via fresh OOF recomputation (`artifacts/metrics/pr_curves.json`, `precision_at_k_curves.json`)
- `src/paimana/app/common.py` — `@st.cache_data` loaders, the persistent synthetic-data banner, `latest_snapshot_per_project` (a dependency-free reimplementation kept local so the app never imports `paimana.models.explain`, which pulls in `shap`)
- `src/paimana/app/Home.py` — **Portfolio Overview**: KPI tiles, risk-band donut, sector risk heatmap, state breakdown
- `src/paimana/app/pages/2_Early_Warning_Centre.py` — filterable/sortable alert queue, severity chips, CSV export, per-project SHAP reason codes
- `src/paimana/app/pages/3_Project_Deep_Dive.py` — predicted-vs-approved cost with an uncertainty band, risk trajectory, SHAP waterfall, delay-reason timeline
- `src/paimana/app/pages/4_Model_Lab.py` — bake-off table, full per-family metrics, calibration curves, PR curves, Precision@K
- `src/paimana/app/pages/5_Assistant.py` — Phase 7 placeholder, clearly labelled
- `tests/test_app_smoke.py` (9 tests) — imports every page, asserts every artifact exists, and **guards that no page ever imports xgboost/lightgbm/shap/statsmodels/sklearn** — the regression test for the cold-start architecture this whole phase depends on

### DoD verification (commands actually run)
```
$ python -m pytest tests/test_app_smoke.py -q
.........                                                                [100%]
9 passed in 6.17s (later 9 passed in 6.52s after the reason-codes fix)

$ streamlit run src/paimana/app/Home.py --server.headless true --server.port 8501
[clean startup log, no errors, "You can now view your Streamlit app..."]

$ curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501
200

$ python -m pytest -q          # full repo suite
179 passed in 567.94s (0:09:27)

$ ruff check src/ tests/ scripts/
All checks passed!
```
- [x] pytest green (179 passed — full repo suite)
- [x] ruff clean
- [x] **Cold start measured directly: 1.69 seconds** (PRD SC-5: <5s) — timed on a genuinely fresh process on a clean port, not the already-warm dev server

### Visual check (mandatory, performed live via the browser tool)
All 5 screens loaded and were screenshotted/inspected directly in a running browser session (not merely imported):
- **Portfolio Overview**: KPI tiles (1,981 projects, ₹2,131.6k cr outlay, 585 at risk, 19.5% avg predicted overrun), donut chart (70.5%/23.9%/5.7% Green/Amber/Red), sector bar chart, state breakdown — all rendering with real numbers, banner visible.
- **Early Warning Centre**: filters, severity chips (265 Critical/511 High/3,877 Medium), sortable table, CSV export button, reason-code drill-down — confirmed working after the fix below.
- **Project Deep-Dive**: uncertainty-band chart, risk trajectory with coloured Green/Amber/Red bands, SHAP waterfall with real signed feature contributions, delay-reason timeline heatmap — all four sub-charts verified with real per-project data.
- **Model Lab**: bake-off table matching Phase 4's BAKEOFF.md numbers exactly, full per-family metrics, calibration curves tracking the diagonal, PR curves, Precision@K curves.
- **Assistant**: placeholder renders correctly, clearly marked "Coming in Phase 7," banner present.

No exceptions or tracebacks on any screen. The synthetic-data banner is present and correctly worded on every screen.

### Key decisions & deviations from PRD
1. **Added `scripts/run_dashboard_data.py`** — not an explicit Phase 6 PRD task by that name, but a necessary consequence of the non-negotiable "zero model training or SHAP computation at request time": the Deep-Dive's uncertainty band and the Model Lab's PR/Precision@K curves need data neither Phase 4 nor Phase 5 cached (only the quantile *models* and *aggregate* metrics were saved). Precomputing this once, the same way Phase 5's backtest precomputed OOF predictions, keeps the dashboard itself artifact-only.
2. **`common.py` deliberately never imports `paimana.models.explain`/`ml`/`baselines`** even though `explain.latest_snapshot_per_project` already exists and does the same thing — importing it would transitively import `shap`, adding avoidable cold-start cost for a three-line function. Reimplemented locally instead. This paid off directly: the 1.69s cold start and the `test_app_never_imports_heavy_ml_modules` guard are the same architectural bet.

### Three real bugs found by clicking through the running app — not assumed fixed after tests passed
1. **A single-quarter uncertainty-band spike.** Project Deep-Dive's cost chart showed p90 jumping to ~1419cr for one quarter against neighbours around ~848cr. Verified against the cached `quantile_predictions.parquet` before treating it as real (it was — a genuine unconstrained-quantile-regression instability, not a plotting bug). Fixed with **display-only** 3-quarter rolling-median smoothing, disclosed in a caption; the underlying parquet is untouched.
2. **Reason codes invisible in the running app despite existing on disk.** `isinstance(c, list)` — the natural check to write — silently matched **zero** of the 256 real cached SHAP explanations, because pyarrow round-trips a parquet list-of-struct column back as `numpy.ndarray`, not a native Python `list`. Caught by literally clicking "show reason codes" and seeing "none available" when I knew from direct inspection that 256 existed. Fixed with a `len()`-based check; added `test_reason_codes_survive_the_real_parquet_round_trip`, which loads the **actual** `alerts.parquet` (not an in-memory fixture) specifically because the bug only exists post-round-trip.
3. **Same root cause, second symptom.** `pd.DataFrame(ndarray_of_dicts)` produces one column of raw dict reprs instead of expanding `feature`/`shap_value` into columns — unlike `pd.DataFrame(list_of_dicts)`. Verified the difference directly before fixing with an explicit `list(...)` wrap.

### Known issues / debt carried forward
- Same PRD Open Item O-1 (unverified calibration anchors) — unaffected by this phase.
- The Portfolio Overview's `st.metric` delta arrow for "Projects at risk" renders green/up-arrow by default for an increase, which isn't semantically "good" here — cosmetic, not fixed (Streamlit's default delta coloring, not a data or logic issue).
- `run_dashboard_data.py` takes a few minutes to run (3 fresh OOF classifier recomputations) — same category as Phase 5's backtest: a deliberate one-off precompute, not something to re-run casually. Re-run it if the underlying models are ever retrained.
- The Model Lab's "Conventional-baseline model cards" section is a one-line pointer to `artifacts/metrics/cards/*.md` rather than rendering their content inline — acceptable for the MVP cut line, could be inlined later if time permits.

### ⏭️ NEXT AGENT STARTS HERE
**Phase 7: LLM Assistant & Demo Hardening.** Read PRD §7/Phase 7 in full before starting. **This phase is explicitly droppable** — Phases 1-6 are already a complete submission.

Preconditions already satisfied:
- The dashboard runs and all 5 screens work; `pages/5_Assistant.py` has the exact placeholder UI to replace with a real chat interface.
- `requirements-assistant.txt` (Phase 1) has the Phase 7 deps (`ollama`, `sentence-transformers`, `jinja2`) — not yet installed; install when Phase 7 begins.
- `docs/DATA_METHODOLOGY.md`, `LICENSES.md`, and every other artifact the assistant might narrate are already in place and internally consistent.

First command to run:
```bash
ollama --version || echo "Ollama not installed — plan for fallback-only mode per PRD R3"
```

Gotchas:
- **Llama models are explicitly rejected** (LICENSES.md, not OSI-approved) — pull `qwen2.5:7b-instruct` (Apache-2.0), not any Llama variant.
- **ChromaDB was deliberately dropped in Phase 1** (native-build dependency issue on this machine) in favour of a brute-force numpy cosine-similarity search over the ~2,000-project narrative corpus — don't reach for a vector DB library without re-reading that Phase 1 decision.
- **The anti-hallucination architecture is non-negotiable (PRD §6.9)**: the LLM only ever narrates numbers computed by a small set of whitelisted pandas tools reading the SAME cached artifacts this dashboard already uses (`risk_scores.parquet`, `alerts.parquet`, `comparison.json`, etc.) — it must never compute or estimate a figure itself, and a deterministic Jinja fallback must render identical numbers if Ollama is unavailable, so the assistant screen can never hard-fail during a demo.
- **General lesson from Phases 4-6**: every one of the last three phases caught a real, non-obvious bug specifically by *running the actual thing* (a live backtest, a live dashboard) rather than trusting passing unit tests alone. Budget time in Phase 7 to actually converse with the assistant (and to kill Ollama mid-conversation to verify the fallback) before declaring it done.

---

## PHASE 5 — Risk Scoring & Early Warning Engine
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~3h (slightly over the ~2.5h budget — the two honesty checks below, done properly, cost the extra time)

### What was built
- `src/paimana/config.py` — added `RISK_MAGNITUDE_COST_CAP_PCT`/`RISK_MAGNITUDE_TIME_CAP_MONTHS` (tied to the existing `SEVERE_*` thresholds), `RISK_MOMENTUM_STALL_CAP_QUARTERS`, every `EW_*` rule threshold, `BACKTEST_MIN_LEAD_QUARTERS`
- `src/paimana/risk/score.py` — `normalized_magnitude`, `momentum_penalty`, `risk_band_for_score`, `compute_risk_scores` (the full §6.7 composite, computed for every project-quarter)
- `src/paimana/risk/alerts.py` — `compute_rule_triggers` (7 EW rules + `MODEL-01`), `_dedupe_edge_triggered`, `build_alerts` (severity collapse, SHAP-gated reason codes, recommended actions), `REASON_ACTIONS`/`FEATURE_ACTIONS` mapping tables
- `scripts/run_risk.py` → `data/processed/risk_scores.parquet`, `data/processed/alerts.parquet`
- `scripts/run_alert_backtest.py` — OOF-based lead-time backtest with horizon-stratified Precision@K and first-trigger rule attribution
- `tests/test_risk_score.py` (13 tests), `tests/test_alert_rules.py` (23 tests) — every EW rule proven on a hand-built fixture per PRD's explicit ask

### DoD verification (commands actually run)
```
$ python scripts/run_risk.py
loaded panel: 51,591 rows x 54 cols
Scoring every project-quarter (risk trajectory)...
risk_scores: 51,591 rows -> data/processed/risk_scores.parquet
risk_band
Green    39495
Amber    10196
Red       1900

Building the alert queue (7 EW rules + model-driven, edge-triggered)...
alerts: 4,653 rows -> data/processed/alerts.parquet
severity
Medium      3877
High         511
Critical     265

$ python -m pytest tests/test_risk_score.py tests/test_alert_rules.py -q
....................................                                     [100%]
36 passed in 1.41s

$ python -c "import pandas as pd; a=pd.read_parquet('data/processed/alerts.parquet'); print(a.severity.value_counts()); print(a.head(10).to_string())"
[severity counts + 10-row table with project_id, sector, as_of_date, severity, triggered_rules, risk_score, recommended_action, reason_codes]

$ python scripts/run_alert_backtest.py
[see "Headline results" below]

$ python -m pytest -q          # full repo suite
170 passed in 568.83s (0:09:28)
```
- [x] pytest green (170 passed — full repo suite)
- [x] ruff clean
- [x] artifacts present: `risk_scores.parquet` (2.9MB), `alerts.parquet` (119KB), `alert_backtest_lead_times.parquet` (6.3KB)

### Headline backtest results (full scale, honest OOF predictions)
| Metric | Value |
|---|---|
| Severe (eventually) completed projects | 237 |
| Flagged by any signal at some point | 206 (86.9%) |
| Median lead time among flagged projects | **18.0 quarters** (4.5 years) before completion |
| Recall @ ≥4 quarters lead time | **81.4%** (193/237) of all eventual severe overruns |
| Precision@25, blended across all quarters | 100.0% (but see caveat below) |
| Precision@25, 0–25% elapsed (hardest horizon) | **88.0%** (18.7% base rate → 4.69x lift) |
| First-trigger attribution | `EW-06` (3+ delay reasons) catches the plurality — 133/206 projects, 22.3q avg lead |

### Key decisions & deviations from PRD
1. **`compute_risk_scores` scores the FULL panel** (all 51,591 rows, completed and ongoing alike), unlike Phase 4's SHAP which was correctly scoped to one row per project. This is deliberate and correct: risk scoring is cheap (a few `.predict()` calls), and PRD §6.1 explicitly wants a risk *trajectory* over time for the dashboard — that requires every historical quarter, not just the latest.
2. **Two real issues found and fixed by checking, not assuming:**
   - **Temporal-correctness bug in reason codes.** The first `build_alerts` implementation attached a project's SHAP reason codes (cached for its *current* latest snapshot only) to *every* historical alert row for that project — a 2007 alert would display "why it fired" using information computed from 2026 data. Fixed by gating the SHAP lookup to the one row that genuinely is the project's latest snapshot (`_is_latest_snapshot`); a dedicated test (`test_reason_codes_only_attach_to_the_true_latest_snapshot`) now proves this directly.
   - **A misleading-if-unqualified headline metric, caught before reporting it.** The backtest's blended Precision@25/50/100 came back at a suspicious 100%/100%/98%. Investigated rather than accepted: the top-ranked rows averaged `elapsed_frac`=1.36 (36% *past* planned completion) with a 100% severe rate — the metric was dominated by trivially-easy "the project is obviously already overdue" cases, not genuine early warning. Added horizon-stratified Precision@K (reusing the same `horizon_bucket` principle as PRD §6.2.3); the honest early-horizon (0–25% elapsed) result is a still-strong 88% — a real finding, reported with the caveat that led to finding it, not hidden.
3. **The backtest recomputes OOF predictions fresh** (via Phase 4's already-tested `classifier_oof_calibrated`/`regressor_oof`, with the exact best family+hyperparameters read back from `comparison.json`) rather than reusing the final in-sample-fit serialized models. Evaluating "would we have caught this early" against a model partly trained on the same historical rows would overstate performance — the honest question is what a model that never saw this specific project would have flagged.
4. **`MODEL-01`** (risk score in the Red band) was added as an eighth trigger alongside the seven explicit EW rules — PRD §6.8 asks for "the seven EW rules **+ model-driven alerts**," and this is the natural reading: the composite score itself can be alert-worthy even when no single narrative rule matches.
5. **Edge-triggering (rising-edge only) for all 8 rules** — not explicitly required by the PRD's rule table, but directly implied by "dedupe/suppress repeats" in the Phase 5 task list; implemented via a per-rule `shift(1, fill_value=False)` comparison per project.

### Known issues / debt carried forward
- Same PRD Open Item O-1 (unverified calibration anchors) — unaffected by this phase.
- `reason_codes` is `None` for 4,397 of 4,653 alerts (only the 256 alerts that happen to land exactly on a project's current latest-snapshot date have cached SHAP available) — this is correct per the temporal-correctness fix, but Phase 6's Early Warning Centre screen should be aware most historical alert rows won't have a SHAP-driven explanation, only the active delay-reason-flag fallback.
- `run_alert_backtest.py` takes ~5–6 minutes per run (4 fresh OOF model fits at full scale) — acceptable as a one-off backtest, but not something to re-run casually; its output (`alert_backtest_lead_times.parquet`) is cached to disk precisely so Phase 6 doesn't need to.
- The recommended-action mapping tables (`REASON_ACTIONS`, `FEATURE_ACTIONS`) are a reasonable first pass, not exhaustively validated against real MoSPI escalation procedures — worth a one-line caveat if presented as prescriptive guidance rather than an illustrative capability.

### ⏭️ NEXT AGENT STARTS HERE
**Phase 6: Streamlit Dashboard — the MVP cut line.** Read PRD §7/Phase 6 in full before starting. Everything through this phase is a complete, submittable product.

Preconditions already satisfied:
- `data/processed/risk_scores.parquet` (51,591 rows — full risk trajectory for every project-quarter) and `data/processed/alerts.parquet` (4,653 alerts, ready for the Early Warning Centre screen) both regenerable via `python scripts/run_risk.py`.
- `artifacts/metrics/comparison.json` / `BAKEOFF.md` — the full Model Lab screen's data.
- `artifacts/metrics/shap_values.parquet` / `shap_global.parquet` — the Project Deep-Dive screen's waterfall and global driver chart.
- `artifacts/metrics/alert_backtest_lead_times.parquet` — the "money slide" data, ready to visualize.

First command to run:
```bash
PYTHONPATH=src /c/dev/paimana-venv/Scripts/python.exe -c "
import pandas as pd
from paimana import config
risk = pd.read_parquet(config.RISK_SCORES_PARQUET)
alerts = pd.read_parquet(config.ALERTS_PARQUET)
print('risk_scores:', risk.shape, '| alerts:', alerts.shape)
print(risk.groupby('project_id')['as_of_date'].max().shape[0], 'unique projects with a current snapshot')
"
```

Gotchas:
- **⚠️ `artifacts/models/` is 235MB** (flagged in the Phase 4 Handoff, still unaddressed) — verify dashboard cold-start time against PRD success criterion SC-5 (<5s) as an early Phase 6 check, not an afterthought. If it's too slow: lazy-load per-screen, or re-tune the winning RandomForest for a smaller footprint.
- **For the "current portfolio" views (Portfolio Overview, Early Warning Centre), filter `risk_scores.parquet`/`alerts.parquet` to each project's LATEST `as_of_date`** — the tables contain the full historical trajectory, not just today's snapshot; use `explain.latest_snapshot_per_project`-style logic (already proven correct in Phase 4/5) rather than re-deriving it.
- **Most historical alerts have `reason_codes = None`** (see Known Issues above) — the UI should gracefully show "no cached explanation available" or fall back to the delay-reason flags for those rows, not assume every alert has a SHAP waterfall.
- **`triggered_rules` and `reason_codes` are native Python list/list-of-dict columns in the parquet files** — confirmed to round-trip correctly via pyarrow's automatic schema inference (tested directly before relying on it), but remember they need `ast`-free direct access (already deserialized objects, not JSON strings) when read back with `pd.read_parquet`.
- **The risk score's `RISK_WEIGHT_*` constants are a policy choice PRD §6.7 explicitly wants displayed in the UI** — don't just show the final number; show (or make available) the weight breakdown so the score is arguable, not a black box.
- **General lesson from Phases 4 and 5, worth carrying into Phase 6 too**: before treating any headline number as a demo slide, ask "is this suspiciously easy, and why?" — both of this phase's real findings (the temporal reason-code bug, the blended-Precision@K trap) were caught exactly by asking that question rather than accepting a clean-looking result.

---

## PHASE 4 — ML Models, Calibration, SHAP & the Bake-Off
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~5h (longer than the ~4h budget — two real performance bugs, described below, cost most of the overrun)

### What was built
- `src/paimana/models/preprocessing.py` — `make_sklearn_preprocessor()`, `FEATURE_CATEGORIES`, `prepare_native_categorical()` (kept for documentation, not used — see deviations)
- `src/paimana/models/ml.py` — `make_regressor`/`make_classifier` (RF/XGBoost/LightGBM, all one-hot), `select_hyperparameters` (small time-boxed grid search), `regressor_oof`/`classifier_oof_calibrated` (OOF GroupKFold, matching Phase 3's protocol), `make_group_aware_calibrated_classifier` (isotonic calibration via a GROUP-AWARE inner GroupKFold), `fit_quantile_model` (XGBoost multi-quantile 10th/50th/90th), `run_all_ml_models` orchestrator
- `src/paimana/models/bakeoff.py` — `paired_bootstrap_ci` (project-level, n=1000), `delong_test` (Sun & Xu 2014 fast algorithm), `run_bakeoff` orchestrator
- `src/paimana/models/explain.py` — `latest_snapshot_per_project`, `compute_shap_values`, `build_shap_artifacts`, `top_reason_codes`, `save_shap_artifacts`
- `src/paimana/models/evaluate.py` — added shared `completed_labelled_rows()` (moved from `baselines.py`, aliased back for compatibility)
- `scripts/run_models.py` — full orchestration, sanity gate, artifact serialization, `comparison.json` + `BAKEOFF.md` writers
- `tests/test_ml.py` (14 tests), `tests/test_calibration.py` (9 tests), `tests/test_bakeoff.py` (10 tests), `tests/test_explain.py` (6 tests) — 39 new tests (41 incl. 2 counted differently across files; 134 total repo-wide)

### DoD verification (commands actually run)
```
$ python scripts/run_models.py
completed rows: 34,414 across 1,330 projects
Selecting hyperparameters + fitting RF/XGBoost/LightGBM (OOF via GroupKFold)...
Running the bake-off (paired project-level bootstrap + DeLong test)...
Computing SHAP explanations for y_severe (latest snapshot per project, incl. ongoing)...
  explaining 1,981 rows, one per project (panel has 51,591)
Computing calibration curves...
Serializing models...

ML significantly beat the conventional baseline on 4/5 targets, significantly lost on 0, and showed no significant difference on 1.
Wrote artifacts/metrics/comparison.json
Wrote artifacts/metrics/BAKEOFF.md
Serialized models to artifacts/models

$ python -m pytest tests/test_ml.py tests/test_calibration.py tests/test_bakeoff.py -q
.........................................                                [100%]
41 passed in 568.20s (0:09:28)

$ python -c "import json; c=json.load(open('artifacts/metrics/comparison.json')); assert c['best_ml']['pr_auc']<=0.95, 'LEAKAGE SUSPECTED'; print(c['headline'])"
ML significantly beat the conventional baseline on 4/5 targets, significantly lost on 0, and showed no significant difference on 1.

$ ls artifacts/models/
cost_overrun_pct_quantile.joblib          time_overrun_months_regressor.joblib
cost_overrun_pct_regressor.joblib         y_cost_overrun_classifier_calibrated.joblib
time_overrun_months_quantile.joblib       y_severe_classifier_calibrated.joblib
                                           y_severe_shap_base_model.joblib
                                           y_time_overrun_classifier_calibrated.joblib
```
- [x] pytest green (134 passed — full repo suite, `python -m pytest -q`)
- [x] ruff clean
- [x] `BAKEOFF.md` contains the comparison table, DeLong table, quantile-coverage table, per-family metrics, calibration-curve pointer, and a plain-English verdict per target — including the honest "no significant difference" result for `y_cost_overrun`

### Headline results (full scale, real numbers)
| Target | Conventional | Best ML | Bootstrap 95% CI (ML − conv) | Verdict |
|---|---|---|---|---|
| cost_overrun_pct (R²) | OLS 0.0062 | RandomForest **0.5324** | [0.487, 0.560] | ML significantly better |
| time_overrun_months (R²) | naive −0.0207 | RandomForest **0.4601** | [0.454, 0.507] | ML significantly better |
| y_cost_overrun (PR-AUC) | logit 0.7209 | RandomForest 0.7162 | [−0.024, 0.014] | **No significant difference** |
| y_time_overrun (PR-AUC) | logit 0.7991 | XGBoost **0.8624** | [0.051, 0.078] | ML significantly better |
| y_severe (PR-AUC) | logit 0.6644 | RandomForest **0.7019** | [0.013, 0.064] | ML significantly better |

Best R² (0.53) and best PR-AUC (0.86) sit comfortably under the leakage sanity gates (0.85 / 0.95) — real headroom, not a near-miss. DeLong's test independently corroborates the two strongest classification wins (`y_time_overrun`, `y_severe`) at p≈0. Quantile intervals show honest under-coverage (71.0%/69.6% observed vs. 80% target) — reported as-is, not adjusted to look better.

### Key decisions & deviations from PRD
1. **Every model family uses one-hot encoding, not XGBoost/LightGBM's native categorical support.** Measured directly: on a representative fold, XGBoost scored R²=0.033 with native categorical vs. 0.256 with one-hot; LightGBM 0.122 vs. 0.242. `preprocessing.prepare_native_categorical` is kept in the codebase (documented, unused) rather than deleted, so the finding and the rejected path are both visible.
2. **Two real performance bugs, found by watching the production run rather than assumed fixed after passing small-scale tests:**
   - The bake-off's bootstrap called the full `evaluate.classification_metrics()` (which scans ~200 F1 thresholds) as its per-iteration metric function — ~430x more expensive than the single PR-AUC value actually needed. At `n_boot=1000 × 2 models × 3 classification targets`, this made the production run stall for **over an hour** before I killed it and diagnosed the cause. Fixed with lightweight `_pr_auc`/`_r2` functions; confirmed 14.7s at realistic scale (~3,600x faster). A permanent regression test (`test_paired_bootstrap_completes_quickly_at_realistic_scale`) guards against this exact class of bug recurring silently.
   - SHAP was computed over the full ~51,591-row historical panel, and **twice** (once for the cached artifacts, again just to fetch the model object for serialization). Corrected to explain each project's **latest snapshot only** (~1,981 rows) — this is a genuine scope correction, not merely a speedup: a project's past quarters are frozen history and cannot receive a new alert, so the "as of now" population is exactly what Phase 5's alert engine and Phase 6's dashboard need. ~26x fewer rows, computed once.
3. **Isotonic calibration uses a GROUP-AWARE inner GroupKFold**, not sklearn's default plain KFold — `make_group_aware_calibrated_classifier` is a named, directly-testable function (not inlined) specifically so `tests/test_calibration.py` could verify zero project-group overlap between a classifier's fit and calibrate portions, rather than trusting a docstring claim.
4. **Hyperparameters are searched once per (family, task type)** on a representative target (`cost_overrun_pct` for regression, `y_severe` for classification) via a quick 3-fold GroupKFold, then reused across every target of that type — an explicit, PRD-anticipated simplification (§7/Phase 4 task 1: "small, time-boxed grid") given hackathon time constraints.

### Known issues / debt carried forward
- **`artifacts/models/` is 235MB** (gitignored, so no repo-bloat concern, but real for Phase 6). `y_severe_classifier_calibrated.joblib` alone is 105MB — a RandomForest(n_estimators=400, max_depth=14) wrapped in `CalibratedClassifierCV` stores 3 internal copies (one per inner calibration fold). **Phase 6 should verify dashboard cold-start time (PRD success criterion SC-5: <5s) against this** — options if it's too slow: lazy-load only the model the active screen needs, reduce the winning RF's `n_estimators` in a follow-up tuning pass, or persist with `joblib.dump(..., compress=3)`.
- Quantile-interval coverage is honestly below its 80% target (71.0% cost, 69.6% time) on the temporal test split. Not fixed in Phase 4 (out of scope — PRD asks for the intervals, not a specific coverage guarantee), but worth a one-line caveat on Phase 6's uncertainty-band chart so the dashboard doesn't imply tighter calibration than the model actually has.
- Same PRD Open Item O-1 (unverified calibration anchors) — unaffected by this phase.
- `select_hyperparameters`' 3-fold quick search and the final 5-fold OOF reporting are the only tuning passes; a production system would tune per-target and probably explore a wider grid than 2 configs/family.

### ⏭️ NEXT AGENT STARTS HERE
**Phase 5: Risk Scoring & Early Warning Engine.** Read PRD §7/Phase 5 in full before starting. **This is the MVP mid-point** — Phase 6 (dashboard) is the cut line.

Preconditions already satisfied:
- `artifacts/models/*.joblib` — calibrated classifiers, regressors, and quantile models, all loadable via `joblib.load(...)`.
- `artifacts/metrics/shap_values.parquet` / `shap_global.parquet` — per-project (latest snapshot) and global SHAP values for `y_severe`, ready to become alert "reason codes."
- `artifacts/metrics/comparison.json` / `BAKEOFF.md` — the full bake-off record, useful for the demo narrative.

First command to run:
```bash
PYTHONPATH=src /c/dev/paimana-venv/Scripts/python.exe -c "
import joblib, pandas as pd
from paimana import config
m = joblib.load(config.ARTIFACTS_MODELS_DIR / 'y_severe_classifier_calibrated.joblib')
shap_df = pd.read_parquet(config.ARTIFACTS_METRICS_DIR / 'shap_values.parquet')
print('model:', type(m).__name__, '| shap rows:', shap_df.shape)
"
```

Gotchas:
- **`shap_values.parquet` only has ONE row per project** (the latest snapshot as of `SIMULATION_TODAY`) — this is deliberate (see deviation #2 above) and is exactly what Phase 5's alert engine needs (explaining a project's CURRENT state), but if Phase 5 or 6 ever wants a historical SHAP trajectory for one project's deep-dive, that needs a fresh, small, single-project SHAP call (cheap — one project, not 1,981) rather than assuming the cached file has history.
- **To score an ongoing project for risk, run it through `y_severe_classifier_calibrated.joblib` (and the other two classifiers) via `.predict_proba()`** — these are already-calibrated `CalibratedClassifierCV` objects, so their probabilities are the ones to use directly in the risk-score formula (PRD §6.7), not raw/uncalibrated scores.
- **The composite risk score (PRD §6.7) needs THREE calibrated probabilities** (`P(cost_overrun)`, `P(time_overrun)`) plus the regression predictions (magnitude) — note `y_cost_overrun`/`y_time_overrun` classifiers exist separately from the `cost_overrun_pct`/`time_overrun_months` regressors; the risk formula in `config.py` (`RISK_WEIGHT_P_COST_OVERRUN` etc.) expects probabilities for the P(...) terms and the regression output for the magnitude term — don't accidentally feed a regression prediction where a probability is expected.
- **Every model expects the exact 37-column `select_features()` output**, in the categorical dtypes `select_features` produces (raw object dtype — the one-hot encoding happens INSIDE each pipeline). Don't pre-encode before calling `.predict()`/`.predict_proba()`.
- **Sanity-gate learning for Phase 5**: if you build any NEW model or heuristic in the risk/alert engine, remember the lesson from this phase — verify actual runtime and output plausibility empirically before considering something "done," especially anything involving a loop over many rows/projects or an aggregate metric computed many times.

---

## PHASE 3 — Conventional Statistical Baselines
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~2.5h

### What was built
- `src/paimana/models/evaluate.py` — `regression_metrics`, `classification_metrics` (with a scanned best-F1 threshold), `precision_at_k`/`lift_at_k` (the alert-queue metric), `reliability_curve`, `horizon_stratified_metrics`
- `src/paimana/models/baselines.py` — `naive_baseline` (train-fold sector mean/base-rate with global fallback), `ols_cost_overrun` (sector-FE OLS on log-cost-ratio, Duan-smearing back-transform, full statsmodels summary), `logistic_target` (L2-regularised, full 37-feature set via a `ColumnTransformer` pipeline fit fresh per fold), `run_all_baselines` orchestrator
- `src/paimana/models/survival.py` — `run_survival_models`: Weibull AFT + Cox PH at project grain, temporal train/test split, concordance index (Cox scored via partial hazard, not `predict_expectation`), plus a `original_duration_months` ablation
- `src/paimana/features/build.py` — added `NUMERIC_FEATURE_COLUMNS` / `CATEGORICAL_FEATURE_COLUMNS` constants for reuse across all future model code
- `scripts/run_baselines.py` — orchestrates everything, writes `artifacts/metrics/baselines.json` and 6 model cards to `artifacts/metrics/cards/`
- `tests/test_baselines.py` (13 tests), `tests/test_evaluate.py` (11 tests)

### DoD verification (commands actually run)
```
$ python scripts/run_baselines.py
Fitting naive / OLS / logistic baselines (OOF via GroupKFold)...
Fitting Weibull AFT / Cox PH survival models (temporal split)...

Model      Target               Key metric            Value        n
--------------------------------------------------------------------
naive      cost_overrun_pct     r2                  -0.0010   34,414
naive      time_overrun_months  r2                  -0.0207   34,414
naive      y_cost_overrun       pr_auc               0.2009   34,414
naive      y_time_overrun       pr_auc               0.4920   34,414
naive      y_severe             pr_auc               0.2588   34,414
ols        cost_overrun_pct     r2                   0.0062   34,414
logit      y_cost_overrun       pr_auc               0.7209   34,414
logit      y_time_overrun       pr_auc               0.7991   34,414
logit      y_severe             pr_auc               0.6644   34,414
weibull_aft months_to_completion c_index(test)        0.9455      731
cox_ph     months_to_completion c_index(test)        0.9469      731

Wrote artifacts/metrics/baselines.json
Wrote model cards to artifacts/metrics/cards

$ python -c "import json; m=json.load(open('artifacts/metrics/baselines.json')); assert {'naive','ols','logit','weibull_aft'} <= set(m); print('assertion passed')"
assertion passed

$ python -m pytest tests/test_baselines.py tests/test_evaluate.py -q
........................                                                 [100%]
24 passed in 36.63s
```
- [x] pytest green (93 passed — full repo suite)
- [x] ruff clean
- [x] artifacts present: `artifacts/metrics/baselines.json` (10KB), 6 model cards in `artifacts/metrics/cards/`

### Artifacts produced
| Path | Description |
|---|---|
| `artifacts/metrics/baselines.json` | naive / ols / logit / weibull_aft / cox_ph metrics, all targets (gitignored, regenerate via `run_baselines.py`) |
| `artifacts/metrics/cards/*.md` | 6 human-readable model cards, including the two honesty notes below |

### Key decisions & deviations from PRD
1. **Every non-survival baseline uses an out-of-fold (OOF) GroupKFold(project_id) protocol**, not a single train/test split or in-sample fit — including the naive baseline's sector means, which are computed from the training fold only (a fold-unaware sector mean would leak each test row's own contribution back into its own comparison point — the classic target-encoding leakage trap). This wasn't explicitly spelled out in PRD §6.3 for every model, but is required by §6.2.1's mandate and is what makes Phase 4's bake-off apples-to-apples.
2. **Two real bugs found and fixed, not papered over:**
   - **Duan (1983) retransformation bias.** Back-transforming OLS's log-scale prediction with a plain `exp()` is biased downward (Jensen's inequality); uncorrected, this made OLS score *worse* than the naive baseline it's supposed to beat, which would have been a false, embarrassing "conventional stats can't even beat a dumb average" result. Fixed with the standard smearing-estimator correction (mean of `exp(training-fold residuals)`).
   - **Unseen-category crash risk in `smf.ols("~ C(sector)")`.** If a GroupKFold training fold happens to contain zero projects from some sector, patsy raises at `predict()` time on any test row using that sector. This didn't show up at the full 1,981-project scale (≈60 projects/sector makes it very unlikely) but was caught immediately by a smaller (600-project) test fixture — exactly the kind of latent bug low test coverage would have shipped silently. Fixed by declaring `sector` as a `pandas.Categorical` with the full `config.SECTORS` vocabulary before fitting, so every fold's design matrix is consistent regardless of composition.
3. **Documented, not hidden, an interpretively awkward result**: Weibull AFT's concordance index (0.9455) is high mostly because `original_duration_months` — a legitimate, non-leaky, at-sanction covariate — mechanically dominates absolute time-to-completion (a 200-month project takes longer in absolute terms than a 20-month one almost regardless of relative risk). An ablation (ran and reported, not asserted) shows concordance drops to 0.7575 without it. This is exactly why `y_time_overrun`/`time_overrun_months` (relative to plan) are Phase 4's harder, more decision-relevant targets — flagged in the model card per this project's intellectual-honesty principles.
4. **OLS is scoped to sector fixed effects only** (per PRD §6.3's literal wording), yielding a small but positive OOF R² (0.0062) — an honest, expected result given the generator's dominant idiosyncratic noise (PRD §4.3.5): sector alone barely predicts an individual project's overrun. The fairer full-feature-set conventional comparison against Phase 4's ML models is the logistic regression results, not this one — noted explicitly in the OLS model card so a reader doesn't mistake a narrow-scope baseline for the best conventional method could do.

### Known issues / debt carried forward
- Same PRD Open Item O-1 (unverified calibration anchors) — unaffected by this phase.
- The naive/logit sanity-gate tests (`test_no_model_exceeds_the_*_sanity_gate`) check against `config.MAX_PLAUSIBLE_R2`/`MAX_PLAUSIBLE_PR_AUC` on the 600-project test fixture, not the full 1,981-project production data — Phase 4 should add an equivalent check against the actual `artifacts/metrics/*.json` output at full scale (e.g. in `scripts/run_baselines.py` itself or a dedicated integration test) so the sanity gate can't silently stop applying to what actually ships.
- `logistic_target`'s `ColumnTransformer` is rebuilt from scratch on every fold (5x per target) — fine at this data scale (a few seconds total) but would need caching/reuse if the feature set or fold count grows substantially in Phase 4.

### ⏭️ NEXT AGENT STARTS HERE
**Phase 4: ML Models, Calibration, SHAP & the Bake-Off.** Read PRD §7/Phase 4 in full before starting.

Preconditions already satisfied:
- `artifacts/metrics/baselines.json` and model cards exist and are regenerable via `python scripts/run_baselines.py`.
- `paimana.models.evaluate` has the full metric suite Phase 4 needs (`regression_metrics`, `classification_metrics`, `precision_at_k`, `horizon_stratified_metrics`) — reuse it, don't reimplement.
- `paimana.features.build.NUMERIC_FEATURE_COLUMNS` / `CATEGORICAL_FEATURE_COLUMNS` are available for consistent encoding.

First command to run:
```bash
PYTHONPATH=src /c/dev/paimana-venv/Scripts/python.exe -c "import json; m=json.load(open('artifacts/metrics/baselines.json')); print(json.dumps({k: {t: v.get('r2', v.get('pr_auc')) for t,v in m[k].items()} for k in ('naive','ols','logit')}, indent=2))"
```
This prints the exact numbers Phase 4's ML models need to beat (or honestly fail to beat — PRD §6.5 explicitly allows "no significant difference" as a legitimate finding).

Gotchas:
- **XGBoost/LightGBM can take `category` dtype natively** — prefer that over one-hot for the tree ensembles (faster, no dimensionality blowup from `sector`'s 22 / `state`'s 36 levels). This is a genuinely different encoding path from `logistic_target`'s `ColumnTransformer`+`OneHotEncoder`; don't reuse that pipeline unchanged for Phase 4.
- **Reuse the OOF GroupKFold protocol**, not a single train/test split, for every ML model — this is what makes the bake-off's paired bootstrap (PRD §6.5) valid: it needs each model's predictions on the SAME held-out rows.
- **The "too good" sanity gate is now armed and real**: `config.MAX_PLAUSIBLE_R2 = 0.85` / `MAX_PLAUSIBLE_PR_AUC = 0.95`. If an XGBoost/LightGBM model exceeds either, per PRD §4.3.5 that is evidence of a leakage bug, not a modelling win — stop and re-check `assert_no_leakage()` and the feature list before reporting the number. Phase 3's naive/logit baselines came in well under both gates (naive R² ≈ 0, logit PR-AUC 0.66–0.80), so there is real headroom for ML to legitimately improve without approaching those ceilings — if a Phase 4 model is anywhere near them, be suspicious first.
- **Remember the two Phase 3 bugs when building the ML pipeline**: (a) any log/ratio-scale prediction needs a bias-aware back-transform, not a plain `exp()`, if you go that route; (b) any categorical handling must use a fixed vocabulary (`config.SECTORS` etc.), not one inferred per-fold, or a rare-category fold will crash exactly like `ols_cost_overrun` did before the fix — XGBoost/LightGBM native categorical support handles this correctly by design, but double-check if using `pd.get_dummies` or `OneHotEncoder` anywhere in Phase 4 too.
- **Precompute and cache SHAP values** (PRD §7/Phase 4 task 3) — this is explicitly flagged in the PRD as a "must precompute, not compute live in Streamlit" concern for Phase 6; don't defer that architectural decision to Phase 6 and discover it's slow then.

---

## PHASE 2 — Feature Engineering & Leakage-Safe Splits
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~2h

### What was built
- `src/paimana/features/leakage.py` — `FORBIDDEN_COLUMNS` (exact match against `schema.TARGET_COLUMNS`) + `FORBIDDEN_PATTERN` regex (`^(final_|revised_|anticipated_|y_|target_)`, forward-compatible with a real CUF extract's likely naming) + `assert_no_leakage()`, the call every downstream phase must make on its actual `X` before fitting/predicting
- `src/paimana/features/build.py` — `ALL_FEATURE_COLUMNS`, `build_feature_table()`, `select_features()`, and the new **agency historical-performance features**: `agency_prior_completed_count`, `agency_prior_avg_cost_overrun_pct`, `agency_prior_avg_time_overrun_months`, `agency_prior_severe_rate` — computed per-agency via `np.searchsorted` over strictly-prior completions
- `src/paimana/features/splits.py` — `grouped_cv()` (GroupKFold by `project_id`), `temporal_split()` (sanction-year cutoff), `horizon_bucket()` (elapsed-fraction quartiles), `assert_no_group_overlap()`
- `src/paimana/data/loader.py` — added `load_processed_features()`
- `scripts/run_features.py`, `scripts/run_split_check.py`
- `notebooks/01_eda.ipynb` — 5 analyses: distributions, sector×cost-band overrun heatmap, delay-reason co-occurrence, `progress_gap_pp` as an early leading indicator, right-censoring (incl. a Kaplan-Meier curve)
- `tests/test_leakage.py` (31 tests), `tests/test_features.py` (16 tests incl. a hand-built agency-fixture), `tests/test_splits.py` (folded into the same 16)

### DoD verification (commands actually run)
```
$ python scripts/run_features.py
loaded panel: 51,591 rows x 50 cols
features: 51,591 rows x 54 cols -> data/processed/features.parquet
model-ready X: 51,591 rows x 37 feature cols (leakage check passed)
rows with at least one prior agency completion on record: 41,978

$ python -m pytest tests/test_leakage.py -v
============================= test session starts =============================
collected 31 items
[... 31 passed ...]
============================= 31 passed in 1.08s ==============================

$ python -m pytest tests/test_features.py tests/test_splits.py -q
................                                                         [100%]
16 passed in 2.26s

$ python scripts/run_split_check.py
labelled rows: 34,414 across 1,330 projects

--- GroupKFold(project_id, n_splits=5) ---
fold 0: train=27,531 test=6,883 fold ok True
fold 1: train=27,531 test=6,883 fold ok True
fold 2: train=27,531 test=6,883 fold ok True
fold 3: train=27,532 test=6,882 fold ok True
fold 4: train=27,531 test=6,883 fold ok True

--- Temporal split (cut_year=2018) ---
train (sanctioned <2018): 29,805 rows
test  (sanctioned >=2018): 4,609 rows

--- Horizon buckets ---
elapsed_frac
0-25%      7259
25-50%     7918
50-75%     7898
75%+      11339
Name: count, dtype: int64

All folds ok: zero project_id overlap between train and test.

$ python -m nbconvert --to html --execute notebooks/01_eda.ipynb
[NbConvertApp] Converting notebook notebooks/01_eda.ipynb to html
[NbConvertApp] Writing 314900 bytes to notebooks\01_eda.html
```
- [x] pytest green (69 passed — full repo suite, includes all Phase 1 tests still passing)
- [x] ruff clean (`ruff check src/ tests/ scripts/` → "All checks passed!")
- [x] artifacts present: `data/processed/features.parquet` (1.7MB), `notebooks/01_eda.ipynb` + rendered `.html` (322KB, 0 cell errors — confirmed via `grep -c '"output_type": "error"'` returning 0)

### Artifacts produced
| Path | Rows/Size | Description |
|---|---|---|
| `data/processed/features.parquet` | 51,591 rows × 54 cols | Panel + agency track-record features + targets (gitignored) |
| `notebooks/01_eda.ipynb` | 10.8KB source | EDA notebook, committed (the executed `.html` is gitignored, regenerate via nbconvert) |

### Key decisions & deviations from PRD
1. **Pinned `mistune<3.1`** (added `mistune==3.0.2` to `requirements.txt`). `nbconvert==7.16.4`'s HTML exporter subclasses mistune's `BlockParser` with a `SPECIFICATION` entry (`axt_heading`) that mistune 3.1+ renamed to `atx_heading`; a transitively-installed `mistune==3.3.4` broke every `--to html` export with `AttributeError`. Found by actually running the DoD's nbconvert command, not assumed.
2. **Only agency-level historical-performance features were built**, not a parallel sector-level rolling feature — matching PRD Phase 2 task 2's literal scope. Sector itself is already a categorical feature; agency identity has ~130 levels and needed a derived numeric signal to be usable, which is why the PRD singled it out.
3. Self-leakage prevention for the agency track record required no explicit per-row exclusion code: because a project's own panel rows never extend past its own completion date, `np.searchsorted(..., side="left")` on strictly-prior completions makes self-inclusion structurally impossible. This is verified directly in `tests/test_features.py::test_project_never_counts_its_own_completion_as_prior` and `test_project_does_not_see_its_own_future_completion` with a hand-built fixture, not just asserted in a docstring.

### Known issues / debt carried forward
- Same PRD Open Item O-1 as Phase 1 (calibration anchors unverified against a specific published report) — unaffected by this phase.
- `agency_prior_*` features are NaN for the ~19% of rows whose agency has no qualifying prior completion yet (`agency_prior_completed_count == 0`); Phase 3/4 model code must handle this NaN explicitly (median/constant imputation, or a tree-based model that handles NaN natively — XGBoost/LightGBM do).
- `select_features()` currently returns raw categorical columns (`sector`, `state`, etc.) as `object` dtype — Phase 3 (statsmodels/sklearn linear models) and Phase 4 (tree ensembles) have different encoding needs (one-hot vs. native categorical support) and will need their own encoding step; this was deliberately left out of Phase 2 since encoding choice is a modelling decision, not a feature-contract one.

### ⏭️ NEXT AGENT STARTS HERE
**Phase 3: Conventional Statistical Baselines.** Read PRD §7/Phase 3 in full before starting.

Preconditions already satisfied:
- `data/processed/features.parquet` exists (51,591 rows × 54 cols); load via `paimana.data.loader.load_processed_features()`.
- `paimana.features.build.select_features(df)` returns a leakage-checked `X`; `paimana.features.splits` provides `grouped_cv`, `temporal_split`, `horizon_bucket`.
- Venv has all core deps including `statsmodels` and `lifelines` (both already installed and used by the EDA notebook's Kaplan-Meier curve).

First command to run:
```bash
PYTHONPATH=src /c/dev/paimana-venv/Scripts/python.exe -c "from paimana.data.loader import load_processed_features; from paimana.features.build import select_features; df = load_processed_features(); print(df.shape); print(select_features(df).dtypes.value_counts())"
```
(Note: bare `python -c` needs `PYTHONPATH=src` — only pytest gets the path for free via `pyproject.toml`'s `pythonpath` ini option. Scripts under `scripts/` handle this themselves via `sys.path.insert`.)

Gotchas:
- **Drop or impute NaN targets/features before fitting anything.** `y_severe`/`cost_overrun_pct`/etc. are null for the ~34% still-censored rows (by design — see Phase 1 methodology); `agency_prior_*` features are null for ~19% of rows with no agency track record yet. `scripts/run_split_check.py` already shows the pattern: `df.dropna(subset=["y_severe"])` before building `X`/`y`.
- **Categorical encoding is NOT yet decided.** `select_features()` returns `sector`/`state`/`funding_mode`/`implementing_agency_type`/`cost_band` as raw strings. statsmodels' OLS/logit will need `pd.get_dummies` or a formula-API categorical spec; XGBoost/LightGBM can take `category` dtype natively (faster, no dimensionality blowup) — Phase 4 should prefer that path over one-hot if using those libraries directly.
- **Survival analysis needs a different data shape.** `lifelines`' `WeibullAFTFitter`/`CoxPHFitter` want ONE ROW PER PROJECT (`months_to_completion`, `is_censored`) with static covariates — that's `projects.parquet`/`load_processed_projects()`, not the panel. Don't try to feed the quarterly panel directly into a survival model without first collapsing to project grain (or explicitly choosing a time-varying-covariate survival formulation, which is a bigger scope decision — flag it to the user if considering that route).
- **`GroupKFold` needs a non-null, equal-length `y`.** If a model target has nulls, filter rows before calling `grouped_cv`, exactly as `run_split_check.py` does — don't pass NaN-containing `y` into `GroupKFold.split()`.
- The naive baseline (global/sector mean) is listed FIRST in PRD §6.3 for a reason: it's the floor every later model — including the "conventional" OLS/logit — must beat. Compute and report it before anything else in `models/baselines.py`.

---

## PHASE 1 — Foundation & Synthetic Data Engine
**Status:** ✅ COMPLETE
**Date:** 2026-09-12
**Duration:** ~2.5h

### What was built
- `.gitignore` — excludes venv, data/artifacts (regenerable), notebook outputs
- `requirements.txt` — core deps for Phases 1–6 (pandas, sklearn, xgboost, lightgbm, shap, lifelines, statsmodels, streamlit, plotly, pytest, ruff, jupyter)
- `requirements-assistant.txt` — Phase 7 extras (ollama, sentence-transformers, jinja2), deliberately separated — see Deviations below
- `pyproject.toml` — pytest `pythonpath=src`, ruff config
- `src/paimana/config.py` — paths, `RANDOM_SEED=42`, `SIMULATION_TODAY=2026-09-12`, portfolio structure (sectors/states/funding modes), PRD §4.4 calibration anchors, PRD §6.7 risk weights, sanity-gate thresholds
- `src/paimana/data/schema.py` — CUF column contract (STATIC/SNAPSHOT/TARGET column tuples), enums, typed dataclasses — single source of truth for column names across the whole pipeline
- `src/paimana/data/generator.py` — the synthetic panel generator (see methodology doc)
- `src/paimana/data/loader.py` — `load_panel(source="synthetic"|"real")` adapter; `"real"` raises `NotImplementedError` naming the exact required schema
- `src/paimana/data/validate.py` — `AnchorCheck`/`compute_fidelity_report`/`assert_fidelity` — the aggregate-fidelity build gate
- `scripts/run_generate.py`, `scripts/run_validate.py` — CLI entrypoints
- `docs/DATA_METHODOLOGY.md` — full generative methodology, every assumption labelled, including the two calibration bugs found and fixed this phase
- `LICENSES.md` — OSI audit table (core + Phase 7 extras + rejected candidates with reasons)
- `README.md` — project skeleton, quickstart, architecture summary
- `tests/test_schema.py`, `tests/test_generator.py`, `tests/test_validate.py` — 22 tests

### DoD verification (commands actually run)
```
$ python -c "import pandas, numpy, sklearn, xgboost, lightgbm, shap, lifelines, statsmodels, streamlit, plotly; print('deps ok')"
deps ok

$ python scripts/run_generate.py
Generating synthetic panel (seed=42, n_projects=1981)...
projects: 1,981 rows x 24 cols -> data/processed/projects.parquet
panel:    51,591 rows x 50 cols -> data/processed/panel.parquet
unique projects in panel: 1,981
censored (ongoing) share: 32.9%

$ python -c "import pandas as pd; d=pd.read_parquet('data/processed/panel.parquet'); print(d.shape); assert d.shape[0]>50000; assert d.project_id.nunique()==1981; print('grain ok')"
(51591, 50)
grain ok

$ python -m pytest tests/test_schema.py tests/test_generator.py tests/test_validate.py -q
......................                                                   [100%]
22 passed in 11.72s

$ python scripts/run_validate.py
Anchor                                            Target   Observed                   Band   Status
----------------------------------------------------------------------------------------------------
n_projects                                      1981.000   1981.000   [1981.000, 1981.000]     PASS
n_sectors                                         22.000     22.000       [22.000, 22.000]     PASS
share_censored_ongoing                             0.350      0.329         [0.262, 0.438]     PASS
share_cost_overrun (completed subset)              0.200      0.161         [0.150, 0.250]     PASS
share_time_overrun (completed subset)              0.400      0.468         [0.300, 0.500]     PASS
aggregate_cost_overrun_pct (completed subset)     20.000     18.433       [15.000, 25.000]     PASS

All anchors within tolerance.
```
- [x] pytest green (22 passed, full repo suite — `python -m pytest -q` also run standalone, same result)
- [x] ruff clean (`ruff check src/ tests/ scripts/` → "All checks passed!")
- [x] artifacts present (`data/processed/panel.parquet` 1.5MB, `data/processed/projects.parquet` 117KB — verified via `ls -la`)

### Artifacts produced
| Path | Rows/Size | Description |
|---|---|---|
| `data/processed/panel.parquet` | 51,591 rows × 50 cols | Project-quarter snapshots (gitignored, regenerate via `run_generate.py`) |
| `data/processed/projects.parquet` | 1,981 rows × 24 cols | Static attributes + terminal targets (gitignored) |

### Key decisions & deviations from PRD
1. **Split `requirements.txt`.** `chromadb`'s `chroma-hnswlib` dependency requires a native C++ build (MSVC Build Tools not present on this machine) and aborted the *entire* `pip install` batch — nothing installed, not even pandas. Moved `chromadb`, `sentence-transformers`, `ollama`, `jinja2` into `requirements-assistant.txt`, installed only when Phase 7 begins. **Also decided:** drop ChromaDB entirely in favour of a brute-force numpy cosine-similarity search in Phase 7 — the corpus is ~2,000 short project narratives, no vector DB is needed, and it removes a fragile native-build dependency from the demo-day risk surface (PRD risk R3/R4). PRD §3.1 named ChromaDB "(or faiss-cpu)"; this substitutes numpy instead, a stricter simplification in the same spirit.
2. **Sector duration medians stretched 1.75×** (`_DURATION_SCALE_MULT` in `generator.py`) beyond the illustrative per-sector values, to give the panel enough quarters per project to clear the >50,000-row expectation in PRD §5.1 — large infrastructure programmes commonly do run 5–8+ years, so this is a realism correction, not an arbitrary inflation.
3. **Cost overrun outcome uses a portfolio-relative risk-percentile formula**, not a direct function of the quarterly spending "gap." Documented in full in `docs/DATA_METHODOLOGY.md` §6 — required to hit the overrun-share and overrun-magnitude anchors simultaneously (they only coexist under a right-skewed distribution).
4. All deviations are additive engineering corrections within the PRD's stated intent (§4.3.5 "not too good," §5.1 grain and scale) — none change the modelling methodology, the data contract, or the phase plan.

### Known issues / debt carried forward
- **PRD Open Item O-1 still open**: the §4.4 anchors (20% cost-overrun share, 40% time-overrun share, etc.) are illustrative assumptions, not sourced from a specific dated Flash Report. They are one-line changes in `config.py` if/when a real report is checked.
- The generator's calibration constants (`_SECTOR_PROFILE` values, the risk-percentile exponent, onset probabilities) were tuned empirically against the anchors at `n_projects=1981, seed=42` specifically. They are not guaranteed to hold at a materially different `n_projects` or seed — acceptable, since the production dataset always uses the pinned config values.
- `docs/DEMO_SCRIPT.md` and the "Honest limitations" section of `README.md` are placeholders, explicitly scheduled for Phase 7 per the PRD.

### ⏭️ NEXT AGENT STARTS HERE
**Phase 2: Feature Engineering & Leakage-Safe Splits.** Read PRD §7/Phase 2 in full before starting.

Preconditions already satisfied:
- `data/processed/panel.parquet` and `projects.parquet` exist and pass all anchor checks (regenerate anytime with `python scripts/run_generate.py` — deterministic under seed 42).
- Venv is live at `C:\dev\paimana-venv` with all core (Phase 1–6) dependencies installed.
- Schema contract (`paimana.data.schema`) is stable and should be imported from, not re-typed.

First command to run:
```bash
/c/dev/paimana-venv/Scripts/python.exe -c "from paimana.data.loader import load_processed_panel; print(load_processed_panel().shape)"
```

Gotchas:
- **The leakage guard (`features/leakage.py`, `tests/test_leakage.py`) is the single most important thing in Phase 2.** `TARGET_COLUMNS` in `schema.py` lists every forbidden column by name; the regex trap in PRD §5.5 (`^(final_|revised_|anticipated_|y_|target_)`) still needs implementing since the current schema doesn't have `revised_`/`anticipated_` columns yet (only `final_*`/`y_*` exist in this generator) — decide whether to add them defensively for forward-compatibility with a real CUF extract, or scope the regex to what actually exists. Recommend adding them defensively; the real loader (§4.3.4) will need them.
- `expenditure_to_date_cr` and `financial_progress_pct` in the panel are computed against `original_cost_cr` only (never revised/final) — safe to use as features, but re-verify this assumption before trusting it blindly.
- Agency-level historical-performance features (PRD §2 Phase 2 task 2) must only use OTHER projects' data completed strictly before each row's `as_of_date` — this is a second, subtler leakage trap distinct from the target-column blacklist; there is no code for it yet.
- `is_censored` rows have null targets (`pd.NA`/`NaN`/`NaT`) by design (§7 of the methodology doc) — Phase 2/3/4 model-training code must filter or handle these explicitly per task (classification/regression drop them or use them only for survival analysis).
- Reminder: `pytest.ini_options` in `pyproject.toml` sets `pythonpath=["src"]`, so `from paimana...` imports work directly in tests without a `sys.path` hack; scripts under `scripts/` still need the manual `sys.path.insert` (see `run_generate.py` for the pattern) since they're run directly, not via pytest.

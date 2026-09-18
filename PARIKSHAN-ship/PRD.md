# PRD — PARIKSHAN
### Predictive Analytics & Risk Intelligence for Kilo-scale Sanctioned Hackathon projects
**An AI-Powered Predictive Analytics & Early Warning System for the MoSPI PAIMANA Portal**

| Field | Value |
|---|---|
| Document version | 1.0 |
| Date | 2026-09-12 |
| Owner | Project owner (solo) |
| Implementer | Project owner (solo) |
| Status | **APPROVED — Phase 1 may begin** |
| Constraint | 100% open-source (OSI-approved licences only), fully offline-capable |

---

## 0. How to read this document

This PRD is the **single source of truth** for this project's design and methodology.

- §1–§4 = **what** we are building and why.
- §5 = **data contract** (the hardest, most load-bearing section).
- §6 = **modelling methodology**, including the anti-leakage protocol.
- §7 = **7 atomic phases**. Each phase is sized for one fresh context window and ends in a Handoff Report.
- §8 = **Definition of Done** — literal shell commands that must pass. No phase is "done" without them.
- §9 = risks, §10 = what we deliberately are NOT building.

---

## 1. Vision & Scope

### 1.1 The problem in one sentence
PAIMANA tells MoSPI **what has already gone wrong**; it cannot tell them **which project will go wrong next quarter**.

### 1.2 Vision
Convert ~two decades of Common Upload Form (CUF) data into a **leakage-safe, calibrated, explainable early-warning system** that ranks the 1,981 ongoing infrastructure projects by probability of cost and schedule overrun, fires actionable alerts *mid-execution*, and lets a non-technical officer interrogate the portfolio in natural language — running entirely offline on commodity hardware.

### 1.3 The product thesis (the pitch)
> Monitoring answers *"is this project late?"*. We answer *"which 50 of these 1,981 projects should the Secretary review this month, why, and what is the recommended intervention?"*

This reframing matters: MoSPI's real constraint is **reviewer bandwidth**, not information. Our headline metric is therefore **Precision@K**, not accuracy.

### 1.4 MVP scope (hackathon deliverable)

| Priority | Capability | Phase |
|---|---|---|
| **P0 MUST** | Cost-overrun & time-overrun prediction models (regression + classification) | P3, P4 |
| **P0 MUST** | Rigorous AI/ML vs. conventional-statistics bake-off with significance testing | P3, P4 |
| **P0 MUST** | Composite Project Risk Score (0–100, Green/Amber/Red) + Early Warning alert engine | P5 |
| **P1 SHOULD** | Streamlit analyst dashboard (5 screens) | P6 |
| **P2 COULD** | Offline LLM Project Intelligence Assistant (Qwen2.5-7B via Ollama) | P7 |

### 1.5 The MVP cut line
**End of Phase 6 is a complete, demo-able, award-worthy submission.** Phase 7 is a bonus. If time runs out, we stop at a phase boundary and ship — never mid-phase.

### 1.6 Success criteria (measurable)

| # | Criterion | Threshold |
|---|---|---|
| SC-1 | Leakage test suite passes | 100%, zero exceptions |
| SC-2 | Best ML model beats best conventional model on PR-AUC | improvement with 95% bootstrap CI excluding 0 |
| SC-3 | Probability calibration | Brier score better than naive base-rate model; reliability curve plotted |
| SC-4 | Precision@50 on the alert queue | > 2x the portfolio base rate |
| SC-5 | Dashboard cold start | < 5 s to first interactive render |
| SC-6 | LLM assistant numeric fidelity | 100% of quoted figures match pandas ground truth (by construction) |
| SC-7 | Full offline operation | passes with network adapter disabled |
| SC-8 | Licence audit | zero non-OSI dependencies |

---

## 2. Users & Key Journeys

| Persona | Need | Journey |
|---|---|---|
| **MoSPI Monitoring Officer** | "Which projects need my attention *this month*?" | Opens Alerts screen → sorted Red queue → clicks a project → sees SHAP drivers → exports CSV for the ministry |
| **Ministry Nodal Officer** | "Why is *my* project flagged?" | Project Deep-Dive → risk decomposition → predicted vs. approved cost with uncertainty band → top 3 delay drivers |
| **Senior Policy Analyst** | "Is ML actually better than our existing statistics?" | Model Lab screen → head-to-head table, calibration curves, bootstrap CIs, model cards |
| **Secretary / Judge** | "Give me the portfolio in 30 seconds" | Portfolio Overview KPIs + Assistant: *"Which sector has the worst cost overrun this year and why?"* |

---

## 3. Tech Stack (all OSI-licensed — audited)

### 3.1 Core

| Layer | Choice | Licence | Rationale |
|---|---|---|---|
| Language | Python 3.12.10 | PSF | Verified present on machine |
| Env | `venv` at `C:\dev\paimana-venv` | PSF | **MUST live outside Google Drive** — sync locks corrupt site-packages mid-demo |
| Dataframes | pandas, numpy | BSD-3 | — |
| Storage | Apache Parquet via pyarrow | Apache-2.0 | Columnar, typed; DuckDB optional for the scale story |
| Classical stats | statsmodels, scipy | BSD-3 | OLS, logit, diagnostics, hypothesis tests |
| Survival analysis | lifelines | MIT | Cox PH / Weibull AFT for time-to-commissioning — the *correct* conventional method |
| ML | scikit-learn, xgboost, lightgbm | BSD-3 / Apache-2.0 / MIT | — |
| Calibration | sklearn `CalibratedClassifierCV` (isotonic) | BSD-3 | Alerts need probabilities, not scores |
| Explainability | shap | MIT | Global + per-project waterfall = the "prescriptive" layer |
| Dashboard | Streamlit + Plotly | Apache-2.0 / MIT | Fastest path from model to product |
| LLM runtime | Ollama | MIT | Fully local inference |
| LLM weights | **Qwen2.5-7B-Instruct** | **Apache-2.0** | **Llama 3.x is REJECTED — the Llama Community Licence is not OSI-approved** |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | Apache-2.0 | ~80 MB, CPU-fast |
| Vector store | ChromaDB (or faiss-cpu) | Apache-2.0 / MIT | — |
| Testing | pytest, pytest-cov | MIT | DoD enforcement |
| Lint/format | ruff | MIT | — |

### 3.2 Rejected, with reasons (put this slide in the deck)
- **Llama 3.1 / 3.3** — Llama Community Licence carries use restrictions and an MAU clause; it is not OSI open source. Violates the strict constraint.
- **Groq / OpenAI / any hosted API** — violates the constraint, and breaks the offline data-sovereignty argument that makes this credible to a ministry.
- **Prophet / deep time-series networks** — wrong tool. This is tabular panel data over ~2k entities; gradient boosting dominates.
- **React / Next.js frontend** — ~40% of the build budget spent on CSS, zero marks for ML rigour.

### 3.3 Architecture

```
                    +-----------------------------------------+
                    |  DATA LAYER (swappable adapter)         |
                    |  +---------------+   +---------------+  |
                    |  | SyntheticCUF  |   | RealCUFLoader |  |
                    |  |  Generator    |   |  (stretch)    |  |
                    |  +-------+-------+   +-------+-------+  |
                    |          +--------+----------+          |
                    +-------------------+---------------------+
                                        v
                         data/processed/panel.parquet
                         (project x quarter snapshots)
                                        |
                    +-------------------v---------------------+
                    |  FEATURE LAYER                          |
                    |  as-of-t features + LEAKAGE GUARD       |
                    |  GroupKFold(project_id) + temporal split|
                    +-------------------+---------------------+
                          +-------------+-------------+
                          v                           v
              +-----------------------+   +-----------------------+
              | CONVENTIONAL (P3)     |   | MACHINE LEARNING (P4) |
              | Naive / OLS / Logit / |   | RF / XGBoost/LightGBM |
              | Weibull AFT / Cox PH  |   | + isotonic calibration|
              +-----------+-----------+   +-----------+-----------+
                          +-------------+-------------+
                                        v
                          BAKE-OFF: paired bootstrap, 95% CI
                                        |
                    +-------------------v---------------------+
                    |  RISK & ALERT ENGINE (P5)               |
                    |  Composite score 0-100 + rule triggers  |
                    |  + SHAP reason codes + actions          |
                    +-------------------+---------------------+
                          +-------------+-------------+
                          v                           v
              +-----------------------+   +-----------------------+
              | STREAMLIT UI (P6)     |   | LLM ASSISTANT (P7)    |
              | 5 screens + Plotly    |   | Ollama/Qwen2.5 + RAG  |
              +-----------------------+   | NUMBERS FROM PANDAS   |
                                          | ONLY - never the LLM  |
                                          +-----------------------+
```

### 3.4 Repository layout

```
Hackathon/
  PRD.md                      <- this file
  README.md                   <- judged artifact; written P1, polished P7
  LICENSES.md                 <- dependency licence audit
  HANDOFF.md                  <- rolling phase handoff reports
  requirements.txt
  pyproject.toml              <- ruff + pytest config
  src/paimana/
    config.py                 <- all constants, paths, seeds
    data/
      schema.py               <- CUF field contract (single source of truth)
      generator.py            <- synthetic panel generator
      loader.py               <- adapter interface (synthetic | real)
      validate.py             <- aggregate-fidelity checks
    features/
      build.py                <- as-of-t feature construction
      leakage.py              <- FORBIDDEN_FEATURES + guard
      splits.py               <- grouped + temporal splitters
    models/
      baselines.py            <- naive + OLS + logit
      survival.py             <- Weibull AFT / Cox PH
      ml.py                   <- RF / XGB / LGBM + calibration
      evaluate.py             <- metrics, bootstrap CIs, Precision@K
      explain.py              <- SHAP wrappers
    risk/
      score.py                <- composite risk score
      alerts.py               <- rule engine + reason codes
    assistant/
      retriever.py            <- structured + vector retrieval
      tools.py                <- pandas tools the LLM may call
      llm.py                  <- Ollama client + DETERMINISTIC FALLBACK
    app/
      Home.py                 <- Streamlit entrypoint
      pages/
  notebooks/                  <- scientific appendix (01_eda, 02_bakeoff)
  tests/
  data/{raw,interim,processed}/
  artifacts/{models,metrics,figures}/
  scripts/                    <- run_*.py CLI entrypoints
  docs/                       <- DATA_METHODOLOGY.md, DEMO_SCRIPT.md
```

---

## 4. Data Strategy & Intellectual Honesty Protocol

### 4.1 The situation
There is no public, ML-ready, 20-year tabular export of PAIMANA/OCMS project data; Flash Reports are published as PDFs. We therefore **generate synthetic panel data** that mirrors the real CUF schema.

### 4.2 The risk, stated plainly
A model trained on synthetic data measures **how well the learner recovers the rules the generator was given**. Reporting "89% accuracy" as though it were a real-world finding is scientifically void, and a sharp judge will detect it.

### 4.3 The mandated defence (non-negotiable)
1. **Label it.** A persistent amber banner on every dashboard screen: *"SYNTHETIC DATA — generated to match published PAIMANA aggregate statistics. Methodology: `docs/DATA_METHODOLOGY.md`."*
2. **Document the generative assumptions.** Every distribution, coefficient and correlation is written down, with its source or its status as an assumption.
3. **Reframe the claim.** We do not claim predictive accuracy on Indian infrastructure. We claim: *a validated, leakage-safe methodology and a production-ready pipeline, benchmarked on data calibrated to published aggregates, with a one-line switch to the real CUF extract.*
4. **Make the switch real.** `loader.py` exposes `load_panel(source: Literal["synthetic","real"])`. The `real` branch is implemented against the documented schema and raises a clear `NotImplementedError` listing exactly which columns it needs. Judges can see the socket.
5. **Never overfit the story.** The generator injects noise, unexplained variance, missingness and a regime shift so no model can exceed a realistic ceiling. Target: best model R² in the 0.45–0.70 band, PR-AUC 0.65–0.80. **A model that scores higher is a bug, and the test suite treats it as one.**

### 4.4 Calibration anchors
The generator is tuned so portfolio aggregates land near published PAIMANA Flash Report figures. **These anchors live in `config.py` as ASSUMPTIONS and must be sourced/updated from the latest published report in Phase 1.** They are parameters, not facts:

| Anchor | Target | Status |
|---|---|---|
| Ongoing projects | 1,981 | GIVEN |
| Sectors | 22 | GIVEN |
| Cost threshold | > ₹150 crore | GIVEN |
| Share of projects reporting cost overrun | ~20% | ASSUMPTION — verify (O-1) |
| Share of projects delayed vs. original DOC | ~40% | ASSUMPTION — verify (O-1) |
| Aggregate cost overrun as % of original outlay | ~20% | ASSUMPTION — verify (O-1) |
| Delay distribution | right-skewed, long tail past 120 months | ASSUMPTION — verify (O-1) |

`validate.py` asserts that generated aggregates fall within tolerance of these anchors and **fails the build otherwise**.

---

## 5. Data Schema — the CUF Contract

### 5.1 Grain
**One row = one project × one quarter-end snapshot.** ~1,981 projects × up to 80 quarters, filtered to each project's active window. Expected ~60k–120k rows.

This grain is mandatory: an early-warning system must fire *during* execution, which requires the project's state at intermediate times. A single row per project cannot support early warning at all.

### 5.2 Static project attributes (known at sanction)

| Field | Type | Notes |
|---|---|---|
| `project_id` | str | PK component; grouping key for CV |
| `project_name` | str | For UI + LLM retrieval |
| `ministry` | cat | ~22 ministries |
| `sector` | cat | 22 sectors: Railways, Road Transport & Highways, Petroleum, Power, Coal, Atomic Energy, Civil Aviation, Telecommunications, Steel, Mines, Shipping & Ports, Water Resources, Health & Family Welfare, Urban Development, Fertilizers, Chemicals & Petrochemicals, Heavy Industries, Defence, Higher Education, Information & Broadcasting, Textiles, Food & Public Distribution |
| `state` | cat | 36 states/UTs |
| `is_multi_state` | bool | Structural complexity proxy |
| `implementing_agency_type` | cat | CPSU / Department / JV / SPV |
| `agency_id` | cat | Enables agency-level historical-performance features |
| `original_cost_cr` | float | **Approved cost at sanction — the anchor for overrun** |
| `sanction_date` | date | |
| `original_doc` | date | Original Date of Commissioning |
| `original_duration_months` | int | derived: `original_doc - sanction_date` |
| `funding_mode` | cat | Budgetary / IEBR / EAP / PPP |
| `cost_band` | cat | 150–500 / 500–1000 / 1000–5000 / >5000 cr |

### 5.3 Time-varying snapshot fields (as of quarter `t`)

| Field | Type | Notes |
|---|---|---|
| `as_of_date` | date | PK component |
| `elapsed_months` | int | since sanction |
| `elapsed_frac` | float | `elapsed_months / original_duration_months` |
| `physical_progress_pct` | float | 0–100, monotonic non-decreasing |
| `expenditure_to_date_cr` | float | cumulative |
| `financial_progress_pct` | float | `expenditure_to_date_cr / original_cost_cr * 100` |
| `progress_velocity_3q` | float | pp of physical progress per quarter, trailing 3 |
| `progress_gap_pp` | float | `financial_progress_pct - physical_progress_pct` — **the classic leading indicator of cost overrun** |
| `required_velocity` | float | pp/quarter needed to hit `original_doc` |
| `velocity_ratio` | float | `progress_velocity_3q / required_velocity` |
| `stalled_quarters` | int | consecutive quarters with < 0.5 pp progress |
| `reason_flags` | multi-hot | land_acquisition, forest_env_clearance, funds_constraint, contractor_issues, tendering_delay, litigation, r_and_r, law_and_order, geological_surprise, equipment_supply, statutory_clearance, force_majeure |
| `n_reasons_active` | int | |
| `revisions_to_date` | int | count of prior cost/date revisions |
| `months_since_last_revision` | int | |

### 5.4 Target variables (terminal outcomes, joined back to every snapshot)

| Target | Definition | Task |
|---|---|---|
| `cost_overrun_pct` | `(final_cost - original_cost) / original_cost * 100` | regression |
| `y_cost_overrun` | `cost_overrun_pct > 10` | binary classification |
| `time_overrun_months` | `final_doc - original_doc` in months | regression |
| `y_time_overrun` | `time_overrun_months > 6` | binary classification |
| `y_severe` | `cost_overrun_pct > 25 OR time_overrun_months > 24` | binary — **the alert target** |
| `months_to_completion` | for survival models, right-censored for still-ongoing projects | survival |

### 5.5 🚨 FORBIDDEN FEATURES — the leakage blacklist
These columns exist for reporting and **must never enter a training matrix**. `features/leakage.py` holds this list; `tests/test_leakage.py` fails the build if any appears in `X.columns`:

```
revised_cost_cr, anticipated_cost_cr, final_cost_cr, cost_overrun_pct,
anticipated_doc, final_doc, time_overrun_months, y_cost_overrun,
y_time_overrun, y_severe, project_status, completion_date,
plus any column matching ^(final_|revised_|anticipated_|y_|target_)
```

**Subtle traps, also guarded:**
- `expenditure_to_date_cr` and `financial_progress_pct` are legitimate *as-of-t* features **only** when computed against `original_cost_cr` — never against revised/anticipated cost. The generator must not backfill intermediate expenditure from the terminal outcome.
- Agency-level historical-performance features must be computed **only from projects completed strictly before `as_of_date`**, never from the full dataset.

---

## 6. Modelling Methodology

### 6.1 Prediction framing
> Given everything knowable about project *p* as of quarter *t*, predict its terminal cost overrun and schedule overrun.

This yields a natural product feature: **risk trajectory over time**, so the dashboard can show a project's risk rising quarter by quarter — visually the most persuasive chart in the demo.

### 6.2 Validation protocol (mandatory, enforced in code)
1. **GroupKFold(n_splits=5, groups=project_id)** — no project's snapshots may straddle train and test.
2. **Temporal backtest** — train on projects sanctioned before a cut year, test on those sanctioned after. The honest simulation of deployment.
3. **Horizon stratification** — report metrics separately at `elapsed_frac` in [0–25%], [25–50%], [50–75%], [75–100%]. Early prediction is hard and valuable; late prediction is easy and useless. *Most teams will not do this; it is a differentiator.*

### 6.3 Model roster

**Conventional (Phase 3)**
- `NaiveBaseline` — global mean / sector mean overrun (the floor every later model must beat)
- `OLS` on `log1p(cost_ratio)` with sector fixed effects (statsmodels, full summary table)
- `LogisticRegression` with regularisation for binary targets
- `WeibullAFTFitter` + `CoxPHFitter` (lifelines) for time-to-commissioning with right-censoring

**Machine learning (Phase 4)**
- `RandomForest`
- `XGBoost` (+ quantile objective for 10th/90th percentile prediction intervals)
- `LightGBM`
- Isotonic calibration on all classifiers; **calibrated probabilities are a hard requirement** for the alert engine

### 6.4 Metrics

| Task | Metrics |
|---|---|
| Regression | MAE, RMSE, R², MAPE (zero-guarded), prediction-interval coverage |
| Classification | PR-AUC (**primary**), ROC-AUC, Brier, reliability curve, F1 at a tuned threshold |
| **Product** | **Precision@K for K ∈ {25, 50, 100}**, lift over base rate, alert-queue stability quarter-to-quarter |
| Survival | Concordance index |

### 6.5 Significance testing (the differentiator)
"XGBoost got 0.78 vs. logit 0.74" is not a finding. Phase 4 must produce **paired bootstrap resampling at the project level (n=1000)** yielding a 95% CI on the *difference* in PR-AUC, plus a DeLong test for ROC-AUC. The conclusion may legitimately be *"ML is not significantly better for time overrun"* — stating that honestly is worth more to judges than a manufactured win.

### 6.6 Explainability
SHAP TreeExplainer: global beeswarm (portfolio drivers), per-project waterfall (Deep-Dive screen), dependence plots for the top 3 features. SHAP values become the **reason codes** attached to every alert — this is the "prescriptive" layer the problem statement asks for.

### 6.7 Risk score (auditable by construction)
```
risk_score = 100 * (
    0.35 * P(cost_overrun)          # calibrated
  + 0.35 * P(time_overrun)          # calibrated
  + 0.15 * normalised_magnitude     # predicted overrun size, winsorised
  + 0.15 * momentum_penalty         # stall + velocity_ratio shortfall
)
```
Bands: **Green 0–39 / Amber 40–69 / Red 70–100**. Weights live in `config.py`, are displayed in the UI, and are defended in the deck as a **policy choice, not a magic number**. A government system must be arguable, not merely accurate.

### 6.8 Early-warning rules (model + rule hybrid)
Model scores catch learned patterns; explicit rules catch what stakeholders already agree is bad, and make the system trustworthy:

| Rule ID | Trigger | Severity |
|---|---|---|
| `EW-01` | `velocity_ratio < 0.5` for 2 consecutive quarters | High |
| `EW-02` | `progress_gap_pp > 20` (money out, work not done) | High |
| `EW-03` | `stalled_quarters >= 3` | Critical |
| `EW-04` | `risk_score >= 70` and risen >= 15 pts in 2 quarters | Critical |
| `EW-05` | `elapsed_frac > 0.8` and `physical_progress_pct < 60` | High |
| `EW-06` | >= 3 active delay reasons | Medium |
| `EW-07` | 2+ prior revisions and rising predicted overrun | Medium |

Every alert carries: `project_id`, `as_of_date`, `rule_id`, `severity`, `risk_score`, top-3 SHAP reason codes, and a **recommended action** mapped from the dominant reason (e.g. `land_acquisition` → "escalate to State Land Acquisition Cell; convene inter-departmental review").

### 6.9 LLM assistant architecture — the anti-hallucination guarantee
**The LLM never computes or invents a number.**

1. User asks a question in natural language.
2. An intent router (rules + MiniLM embeddings) maps it to one of ~10 whitelisted **pandas tools** (`top_risk_projects`, `sector_summary`, `project_detail`, `alert_digest`, `compare_sectors`, …).
3. The tool executes against the dataframe and returns **structured, verified numbers**.
4. The LLM receives those numbers and only **narrates** them into prose.
5. If Ollama is unreachable, a **deterministic Jinja template** renders the same numbers. **The demo cannot fail.**

This is a defensible architecture, not a limitation — and it is the honest answer to "how do you stop it hallucinating statistics?"

---

## 7. Phase-by-Phase Execution Plan

Seven atomic phases. Each is one fresh context window. Each ends with a Handoff Report appended to `HANDOFF.md`. **Do not start a phase before its predecessor's DoD commands pass.**

---

### PHASE 1 — Foundation & Synthetic Data Engine
**Budget ~3h · Depends: none**

**Goal:** a reproducible environment and a defensible panel dataset.

Tasks:
1. `git init`; `.gitignore` (exclude `data/`, `artifacts/models/`, `__pycache__`, `*.venv`).
2. Create venv at `C:\dev\paimana-venv` (**outside Google Drive** — sync locks corrupt site-packages). Write `requirements.txt` with pinned versions; install.
3. `src/paimana/config.py` — paths, `RANDOM_SEED=42`, the §4.4 calibration anchors, the §6.7 risk weights.
4. `src/paimana/data/schema.py` — the §5 contract as typed dataclasses/enums. Single source of truth.
5. `src/paimana/data/generator.py` — synthetic panel generator:
   - sample static attributes with realistic sector/cost/duration correlations;
   - simulate quarterly execution with sector- and agency-level latent effects, stochastic delay-reason onset, progress dynamics, and a **regime-shift window** so the data is not trivially learnable;
   - derive terminal outcomes; leave ~35% of projects right-censored (still ongoing) for survival modelling;
   - inject realistic missingness (5–12% on progress fields).
6. `src/paimana/data/loader.py` — `load_panel(source="synthetic"|"real")`; the `"real"` branch raises `NotImplementedError` naming required columns.
7. `src/paimana/data/validate.py` — assert generated aggregates fall within tolerance of the §4.4 anchors.
8. `docs/DATA_METHODOLOGY.md` — every generative assumption written down.
9. `README.md` skeleton, `LICENSES.md` audit table.
10. `scripts/run_generate.py` → writes `data/processed/panel.parquet` + `projects.parquet`.

**Definition of Done — all must pass:**
```bash
python -c "import pandas, numpy, sklearn, xgboost, lightgbm, shap, lifelines, statsmodels, streamlit, plotly; print('deps ok')"
python scripts/run_generate.py
python -c "import pandas as pd; d=pd.read_parquet('data/processed/panel.parquet'); print(d.shape); assert d.shape[0]>50000; assert d.project_id.nunique()==1981; print('grain ok')"
python -m pytest tests/test_schema.py tests/test_generator.py tests/test_validate.py -q
python scripts/run_validate.py
```
**Visual check:** the fidelity table prints generated vs. target for every anchor in §4.4; `run_validate.py` exits non-zero on breach.

---

### PHASE 2 — Feature Engineering & Leakage-Safe Splits
**Budget ~3h · Depends: P1**

Tasks:
1. `features/leakage.py` — `FORBIDDEN_FEATURES` list + regex patterns + `assert_no_leakage(X)`.
2. `features/build.py` — as-of-t features per §5.3: velocities, gaps, ratios, stall counters, reason multi-hots, agency historical-performance features (**computed only from projects completed strictly before `as_of_date`**).
3. `features/splits.py` — `grouped_cv(groups=project_id)`, `temporal_split(cut_year)`, `horizon_bucket(elapsed_frac)`.
4. `notebooks/01_eda.ipynb` — distributions, sector overrun heatmap, delay-reason co-occurrence, correlation of `progress_gap_pp` with terminal overrun, censoring analysis.
5. `scripts/run_features.py` → `data/processed/features.parquet`.

**Definition of Done:**
```bash
python scripts/run_features.py
python -m pytest tests/test_leakage.py -v
python -m pytest tests/test_features.py tests/test_splits.py -q
python scripts/run_split_check.py
jupyter nbconvert --to html --execute notebooks/01_eda.ipynb
```
**Visual check:** `test_leakage.py` is 100% green (this is the build gate); `run_split_check.py` prints `fold ok True` for every fold, proving zero `project_id` overlap between train and test; the EDA HTML renders.

---

### PHASE 3 — Conventional Statistical Baselines
**Budget ~2.5h · Depends: P2**

Tasks:
1. `models/baselines.py` — naive (global mean, sector mean), OLS with sector fixed effects, regularised logistic.
2. `models/survival.py` — Weibull AFT + Cox PH with right-censoring; concordance index.
3. `models/evaluate.py` — the §6.4 metric suite including **Precision@K** and horizon-stratified reporting.
4. `scripts/run_baselines.py` → `artifacts/metrics/baselines.json` + model cards in `artifacts/metrics/cards/`.
5. Report the full OLS summary (coefficients, p-values, R², residual diagnostics) — this is the "conventional methods" evidence the problem statement explicitly asks for.

**Definition of Done:**
```bash
python scripts/run_baselines.py
python -c "import json; m=json.load(open('artifacts/metrics/baselines.json')); assert {'naive','ols','logit','weibull_aft'} <= set(m); print(json.dumps(m, indent=2)[:2000])"
python -m pytest tests/test_baselines.py tests/test_evaluate.py -q
```
**Visual check:** a printed metrics table with one row per model per target, naive baseline included as the floor.

---

### PHASE 4 — ML Models, Calibration, SHAP & the Bake-Off
**Budget ~4h · Depends: P3**

Tasks:
1. `models/ml.py` — RF / XGBoost / LightGBM; grouped-CV hyperparameter search (small, time-boxed grid); XGBoost quantile models for 10th/90th prediction intervals.
2. Isotonic calibration for all classifiers; reliability curves.
3. `models/explain.py` — SHAP TreeExplainer; cache global values to `artifacts/metrics/shap_global.parquet`. **Computing SHAP live in Streamlit will kill the demo — precompute everything.**
4. **Bake-off harness:** paired project-level bootstrap (n=1000) → 95% CI on metric *differences*; DeLong test for ROC-AUC.
5. `scripts/run_models.py` → serialised models in `artifacts/models/`, `artifacts/metrics/comparison.json`, human-readable `artifacts/metrics/BAKEOFF.md`.
6. **Sanity gate:** if any model exceeds R² 0.85 or PR-AUC 0.95, the run **fails** with a leakage warning (per §4.3.5).

**Definition of Done:**
```bash
python scripts/run_models.py
python -m pytest tests/test_ml.py tests/test_calibration.py tests/test_bakeoff.py -q
python -c "import json; c=json.load(open('artifacts/metrics/comparison.json')); assert c['best_ml']['pr_auc']<=0.95, 'LEAKAGE SUSPECTED'; print(c['headline'])"
cat artifacts/metrics/BAKEOFF.md
ls artifacts/models/
```
**Visual check:** `BAKEOFF.md` contains the comparison table, bootstrap CIs, calibration-curve paths, and a plain-English verdict — including any honest "no significant difference" result.

---

### PHASE 5 — Risk Scoring & Early Warning Engine
**Budget ~2.5h · Depends: P4**

Tasks:
1. `risk/score.py` — the §6.7 composite score computed for every project-quarter → **risk trajectory**.
2. `risk/alerts.py` — the seven §6.8 rules + model-driven alerts; dedupe/suppress repeats; severity ranking; reason codes from cached SHAP; recommended-action mapping table.
3. `scripts/run_risk.py` → `data/processed/risk_scores.parquet`, `data/processed/alerts.parquet`.
4. `scripts/run_alert_backtest.py` — **if we had run this in 2019, what share of eventual severe-overrun projects would we have flagged at least 4 quarters before commissioning?** Lead-time analysis. This is the money slide.

**Definition of Done:**
```bash
python scripts/run_risk.py
python -m pytest tests/test_risk_score.py tests/test_alert_rules.py -q
python -c "import pandas as pd; a=pd.read_parquet('data/processed/alerts.parquet'); print(a.severity.value_counts()); print(a.head(10).to_string())"
python scripts/run_alert_backtest.py
```
**Visual check:** alert-rule logic is unit-tested against hand-built fixtures (each rule fires exactly when it should); the backtest prints median lead time in quarters and recall of severe overruns at ≥4 quarters before completion.

---

### PHASE 6 — Streamlit Dashboard  ⟵ **MVP CUT LINE**
**Budget ~5h · Depends: P5**

Screens:
1. **Portfolio Overview** — KPI tiles (projects, total approved outlay, projects at risk, aggregate predicted overrun), sector risk heatmap, risk-band distribution, state breakdown.
2. **Early Warning Centre** — sortable/filterable alert queue, severity chips, reason codes, recommended actions, CSV export.
3. **Project Deep-Dive** — project selector; predicted vs. approved cost with uncertainty band; risk trajectory line chart; SHAP waterfall; delay-reason timeline.
4. **Model Lab** — the bake-off table, calibration curves, PR curves, horizon-stratified metrics, Precision@K chart, model cards. *This screen wins the rigour marks.*
5. **Assistant** — placeholder in P6, activated in P7.

Non-negotiables: persistent **SYNTHETIC DATA** banner on every screen; `@st.cache_data` on every load; **zero model training or SHAP computation at request time** — read precomputed artifacts only.

**Definition of Done:**
```bash
python -m pytest tests/test_app_smoke.py -q
streamlit run src/paimana/app/Home.py --server.headless true --server.port 8501
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501
```
**Visual check (mandatory, performed by the agent):** load the app in the browser tool, screenshot **all 5 screens**, confirm no exceptions or tracebacks, confirm cold start < 5 s, confirm the synthetic-data banner is visible on every screen. Attach the screenshots to the Handoff Report.

---

### PHASE 7 — LLM Assistant & Demo Hardening
**Budget ~4h · Depends: P6 · DROPPABLE**

Tasks:
1. Verify/install Ollama; pull `qwen2.5:7b-instruct`. **If unavailable or too slow, ship fallback-only — that is an acceptable outcome, not a failure.**
2. `assistant/tools.py` — ~10 whitelisted pandas tools returning structured, verified numbers.
3. `assistant/retriever.py` — intent routing (rules + MiniLM embeddings) + vector search over project narratives.
4. `assistant/llm.py` — Ollama client, streaming, strict system prompt ("**narrate only the supplied numbers; never compute or estimate**"), timeout, and the **deterministic Jinja fallback**.
5. Wire the Assistant screen; show which tool was invoked and the raw numbers alongside the prose (transparency = trust).
6. **Golden test set:** 8 canonical questions with known ground-truth answers; automated assertion that every quoted figure matches pandas.
7. Hardening: `README.md` (problem, architecture, results, how to run, honest limitations), final `LICENSES.md` audit, `docs/DEMO_SCRIPT.md` (a 5-minute beat-by-beat run sheet), reproducibility check from a clean clone.

**Definition of Done:**
```bash
ollama list
python -m pytest tests/test_assistant_tools.py tests/test_golden_questions.py -q
python scripts/run_assistant_eval.py
python scripts/run_offline_check.py
python -m pytest -q
```
**Visual check:** ask the live Assistant 3 questions in the UI; then stop Ollama mid-demo and confirm the fallback still answers correctly with identical numbers.

---

### 7.8 Phase dependency & time map

```
P1 Data --> P2 Features --> P3 Stats --> P4 ML --> P5 Risk --> P6 Dashboard --> P7 LLM
  3h            3h            2.5h        4h        2.5h          5h             4h
                                                         |___ MVP CUT LINE ___|
                                             Total core: 20h  ·  With P7: 24h
```

---

## 8. Definition of Done — Global Gates

A phase is complete only when **all** of the following hold:

1. ✅ Every DoD command for that phase was executed **by the agent**, with real output shown — not predicted, not assumed.
2. ✅ `python -m pytest -q` is green across all tests written so far (no regressions).
3. ✅ `ruff check src/ tests/` is clean.
4. ✅ Artifacts exist on disk at the paths the PRD specifies (verified with `ls`).
5. ✅ No `NotImplementedError`, `TODO`, or stub remains inside the phase's delivered scope (the `real` loader branch in §4.3.4 is the one sanctioned exception).
6. ✅ A Handoff Report is appended to `HANDOFF.md`.
7. ✅ For P6/P7: visual browser verification with screenshots.

**Failing output is reported verbatim, never summarised as success.**

---

## 9. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Target leakage inflates all metrics | **High** | **Critical** | `tests/test_leakage.py` as a build gate; sanity ceiling in P4 |
| R2 | Judges dismiss the work because data is synthetic | Medium | **Critical** | §4.3 honesty protocol; reframe as methodology + pipeline; visible real-data adapter |
| R3 | Ollama absent or slow on the demo machine | **High** | Medium | Deterministic fallback built before the LLM path; P7 is droppable |
| R4 | Google Drive sync corrupts the venv mid-build | Medium | High | venv at `C:\dev\paimana-venv`; `data/` and `artifacts/models/` gitignored |
| R5 | Streamlit recomputes SHAP per request → demo hangs | Medium | High | Precompute all artifacts in P4/P5; the UI is strictly read-only |
| R6 | Scope creep past the cut line | **High** | Medium | P6 is the cut line; stop only at phase boundaries |
| R7 | Calibration anchors are wrong (unverified assumptions) | Medium | Medium | Anchors are labelled parameters in `config.py`, changeable in one line |
| R8 | Live-demo failure | Medium | High | `DEMO_SCRIPT.md`; screenshots of all screens as backup; nothing trained live |
| R9 | Windows path/encoding bugs | Medium | Low | `pathlib` everywhere; explicit UTF-8 on all file I/O |

---

## 10. Explicit Non-Goals (defend the cut line)

- ❌ Authentication, user accounts, RBAC
- ❌ Cloud deployment, Docker/Kubernetes (a `Dockerfile` is a *stretch*, not scope)
- ❌ Real-time ingestion from the live PAIMANA portal
- ❌ PDF scraping of Flash Reports (stretch only, after P7)
- ❌ Mobile-responsive design
- ❌ Fine-tuning any LLM
- ❌ React / Next.js frontend
- ❌ Any paid or hosted API

---

## 11. Open Items to Resolve During Build

| ID | Item | Resolve by |
|---|---|---|
| O-1 | Verify the §4.4 calibration anchors against the latest published PAIMANA Flash Report | P1 |
| O-2 | Confirm machine RAM/GPU to choose Qwen2.5-7B vs. a 3B quantised variant | P7 |
| O-3 | Confirm submission format (repo / deck / video) — drives README and demo weighting | P6 |
| O-4 | Confirm the hackathon deadline date to re-time the phase map | Immediate |

---

**END OF PRD v1.0 — Phase 1 is cleared to begin.**

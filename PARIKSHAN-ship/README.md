# PARIKSHAN

**An AI-Powered Predictive Analytics & Early Warning System for the MoSPI PAIMANA Portal**

> ✅ **Status: complete.** All 7 phases of the PRD are built and verified —
> see [`PRD.md`](PRD.md) for the full specification and
> [`HANDOFF.md`](HANDOFF.md) for the phase-by-phase build history, including
> every real bug found and fixed along the way.

## What this is

PAIMANA tracks 1,981 ongoing infrastructure projects (>₹150 crore) across 22
sectors, but its monitoring is descriptive: it can tell you a project is
already late or over budget, not that it is *about to be*. PARIKSHAN turns
~two decades of Common Upload Form (CUF)-style data into a leakage-safe,
calibrated early-warning system that ranks projects by predicted risk of cost
and schedule overrun, explains *why*, and surfaces the ones that most need
review — reframing the problem from "monitor 1,981 projects" to "which 50
should the Secretary look at this month."

**⚠️ The dataset is synthetic**, generated to match published PAIMANA
aggregate statistics rather than sourced from a real CUF export (none is
publicly available in ML-ready form — see
[`docs/DATA_METHODOLOGY.md`](docs/DATA_METHODOLOGY.md) for the full
methodology and every generative assumption). Every screen of the dashboard
says so. Every metric in this project is framed as *methodology and pipeline*
validation, not a real-world accuracy claim — see PRD §4.3.

**100% open-source.** No paid or hosted APIs anywhere in the pipeline — see
[`LICENSES.md`](LICENSES.md) for the full dependency audit.

## Project documents

| Document | Purpose |
|---|---|
| [`docs/PARIKSHAN_Explained.docx`](docs/PARIKSHAN_Explained.docx) | Plain-language explainer of the whole project — start here if you're non-technical |
| [`docs/PARIKSHAN_Walkthrough.html`](docs/PARIKSHAN_Walkthrough.html) | A narrated, click-through walkthrough — open it in any browser |
| [`PRD.md`](PRD.md) | Full specification: vision, architecture, data schema, modelling methodology, 7-phase execution plan, Definition of Done |
| [`docs/DATA_METHODOLOGY.md`](docs/DATA_METHODOLOGY.md) | Every synthetic-data generative assumption, documented and justified |
| [`LICENSES.md`](LICENSES.md) | OSI-licence audit of every dependency |
| [`HANDOFF.md`](HANDOFF.md) | Phase-by-phase build log with verified DoD output |
| `docs/DEMO_SCRIPT.md` | 5-minute demo run sheet |

## Quickstart

### Option A: one command (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

This creates the virtualenv (outside this folder — if this folder lives
inside a cloud-sync directory like Google Drive/OneDrive/Dropbox, that
sync daemon can lock files and corrupt `site-packages` mid-install, so the
script deliberately puts the venv elsewhere), installs every dependency,
regenerates the full data/model/artifact pipeline from scratch (`data/`
and `artifacts/` are gitignored — a fresh checkout has none of this), and
runs the test suite. Add `-WithAssistant` to also install the offline LLM
Assistant (Ollama + Qwen2.5-7B-Instruct):

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -WithAssistant
```

Missing prerequisites (Python, Ollama) are installed automatically via
`winget` where possible. See the comment header in `install.ps1` for every
step it performs and every flag it accepts (`-VenvPath`, `-SkipTests`).

### Option B: manual steps

```bash
# 1. Create and activate a virtualenv OUTSIDE this project folder
#    (if this folder is inside a cloud-sync directory such as Google
#    Drive/OneDrive/Dropbox, its sync daemon can lock files and corrupt
#    site-packages mid-run)
python -m venv C:\dev\paimana-venv
C:\dev\paimana-venv\Scripts\Activate.ps1   # PowerShell
# or: source /c/dev/paimana-venv/Scripts/activate  # bash

# 2. Install core dependencies (Phases 1-6)
pip install -r requirements.txt

# 3. Generate the synthetic panel dataset
python scripts/run_generate.py

# 4. Check it against the calibration anchors
python scripts/run_validate.py

# 5. Run the rest of the pipeline (data/ and artifacts/ are gitignored —
#    a fresh checkout needs to regenerate all of this)
python scripts/run_features.py
python scripts/run_split_check.py
python scripts/run_baselines.py
python scripts/run_models.py
python scripts/run_risk.py
python scripts/run_alert_backtest.py
python scripts/run_dashboard_data.py

# 6. Run the test suite
python -m pytest -q

# 7. Launch the dashboard
streamlit run src/paimana/app/Home.py
```

**LLM assistant extras** (Phase 7 — droppable; the rest of the system works
fully without it):
```bash
pip install -r requirements-assistant.txt
# torch must be the CPU-only build on Windows — see requirements-assistant.txt
# for why, and LICENSES.md for the licence audit.
pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps
ollama pull qwen2.5:7b-instruct
python scripts/run_assistant_index.py   # builds the project-narrative search index (once)
```

Then, with `ollama serve` running in the background:
```bash
python -m pytest tests/test_assistant_tools.py tests/test_golden_questions.py -q
python scripts/run_assistant_eval.py     # exercises the live Ollama path
python scripts/run_offline_check.py      # confirms zero outbound network calls
```

If Ollama isn't installed, running, or reachable, the assistant screen still
answers every question via a deterministic template with identical numbers
— see [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for a live demonstration
of this fallback.

## Architecture at a glance

```
Synthetic/Real CUF data --> Feature engineering (leakage-safe, as-of-t)
  --> Conventional stats (OLS/logit/survival) vs. ML (RF/XGBoost/LightGBM)
  --> Bake-off with bootstrap significance testing
  --> Risk score + Early Warning alert engine (rules + SHAP reason codes)
  --> Streamlit dashboard (5 screens)
  --> LLM assistant (local, tool-grounded, never invents a number)
```

Full detail in [`PRD.md` §3.3](PRD.md#33-architecture).

## Repository layout

```
src/paimana/       Library code (data, features, models, risk, assistant, app)
scripts/           CLI entrypoints (run_generate.py, run_validate.py, ...)
tests/             pytest suite — the Definition of Done for every phase
notebooks/         Scientific appendix (EDA, bake-off deep-dives)
data/              Generated datasets (gitignored; regenerate via scripts/)
artifacts/         Trained models, metrics, figures (gitignored; regenerate via scripts/)
docs/              Data methodology, demo script
```

## Build status

See [`HANDOFF.md`](HANDOFF.md) for the authoritative, verified phase-by-phase
log. **All 7 phases are complete.** Phases 1-6 (data, features, modelling,
risk scoring, alerting, dashboard) are the MVP cut line (PRD §1.5) — a
complete, demo-able, submittable product on their own. Phase 7 (the offline
LLM assistant) is an additional layer on top of that working system, not a
dependency of it; the dashboard and every metric in it work identically with
or without Ollama installed.

## Results — headline numbers

Pulled directly from the cached artifacts (see [`HANDOFF.md`](HANDOFF.md)
for the full, phase-by-phase verified output):

- **1,981 projects**, ₹21.3 lakh crore total approved outlay; **585 (29.5%)**
  currently flagged Amber or Red risk.
- **Bake-off, magnitude prediction (regression):** ML (Random Forest)
  clearly beats conventional statistics — R²=0.53 vs. 0.006 for cost
  overrun (bootstrap 95% CI on the gap: [0.49, 0.56]), R²=0.46 vs. -0.02 for
  time overrun (CI [0.45, 0.51]).
- **Bake-off, binary classification:** mixed, and reported honestly either
  way — ML did **not** significantly beat logistic regression for
  cost-overrun classification (PR-AUC 0.716 vs. 0.721, CI **includes**
  zero), but **did** for severe-overrun classification (PR-AUC 0.702 vs.
  0.664, CI [0.013, 0.064]).
- **Early-warning backtest:** of 237 historically eventually-severe
  projects, 206 would have been flagged by at least one signal, with a
  median lead time of **18 quarters** — 193 of those early enough (≥4
  quarters ahead) for a recall of **81.4%** at that threshold.
- **Dashboard cold start:** 1.69s, measured directly on a fresh process.
- **LLM assistant:** 8/8 golden questions pass numeric-fidelity verification
  against the live Ollama model (Qwen2.5-7B-Instruct) — see
  `scripts/run_assistant_eval.py`.

## Honest limitations

- **The dataset is entirely synthetic**, calibrated to published PAIMANA
  aggregate statistics — not a real CUF export (see
  [`docs/DATA_METHODOLOGY.md`](docs/DATA_METHODOLOGY.md) for every generative
  assumption). Every metric here validates the *methodology and pipeline*,
  not real-world accuracy on India's actual infrastructure portfolio.
- **Calibration anchors remain unverified against one specific published
  Flash Report** (PRD Open Item O-1) — they were built to match the general
  order of magnitude of publicly discussed PAIMANA aggregates, not
  cross-checked line-by-line against an official release.
- **The ML-vs-statistics bake-off found a genuine null result** for binary
  cost-overrun classification (see Results above) — reported as-is rather
  than omitted or reframed, per this project's methodology discipline.
- **The observed 80% prediction-interval coverage on the test set is ~70%,**
  not 80% (see the `quantile_interval` block in
  `artifacts/metrics/comparison.json`) — the quantile regressor is
  somewhat overconfident; not recalibrated further given the time budget.
- **The embedding layer (MiniLM semantic routing + project-narrative search)
  depends on a working `torch` install**, which had a real, non-obvious
  Windows-specific DLL conflict during this build (see
  [`LICENSES.md`](LICENSES.md) and `HANDOFF.md` Phase 7). It degrades
  gracefully to rule-based routing if torch is unavailable in a given
  process, but the graceful path was itself only discovered to have a gap
  (a bare `except ImportError` that didn't catch the actual `OSError`) by
  running the **full** test suite, not the assistant tests in isolation —
  a reminder that "tests pass in isolation" and "the system works
  end-to-end" are different claims.
- **SHAP reason codes are only available for each project's most recent
  snapshot** (Phase 4's SHAP computation scope), regardless of which of the
  8 rules fired — a historical alert row falls back to the active delay-reason
  flags instead. By design (attaching a *future* SHAP explanation to a past
  alert would be a lookahead bug), but it does mean older alerts in the
  Early Warning Centre are explained less richly than current ones.
- **Numeric fidelity is not the same guarantee as full correctness.** The
  live LLM assistant is checked so that every number it states must trace
  back to the verified tool output — proven necessary, not theoretical: a
  live call once answered "riskiest sector" with a fabricated portfolio
  total that appeared nowhere in the data, and is now caught and replaced
  with the deterministic template automatically (see `HANDOFF.md` Phase 7).
  But the model has also shown a reproducible *reasoning* error the checker
  doesn't catch by design: naming "Shipping & Ports" (risk score 35.7) the
  riskiest sector when "Civil Aviation" (35.8) actually ranks higher — every
  number in that answer is real, so it passes numeric verification, even
  though the claim built from those numbers is wrong. Catching this class of
  error would need a second, claim-level verifier, out of scope here.

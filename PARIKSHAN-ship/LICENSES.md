# Dependency Licence Audit

**Constraint (PRD §3):** every dependency must carry an
OSI-approved licence. No paid or hosted APIs, no API keys, no billing-capable
services, anywhere in this project.

Update this table whenever a dependency is added — check the licence, add
the row, and if it is not OSI-approved, find an alternative rather than
adding it.

## Core dependencies (`requirements.txt` — installed from Phase 1)

| Package | Version | Licence | OSI? | Purpose |
|---|---|---|---|---|
| pandas | 2.2.3 | BSD-3-Clause | ✅ | Dataframes |
| numpy | 1.26.4 | BSD-3-Clause | ✅ | Numerics |
| pyarrow | 17.0.0 | Apache-2.0 | ✅ | Parquet I/O |
| statsmodels | 0.14.4 | BSD-3-Clause | ✅ | OLS/logit, conventional baselines |
| scipy | 1.14.1 | BSD-3-Clause | ✅ | Statistics, hypothesis tests |
| lifelines | 0.29.0 | MIT | ✅ | Survival analysis (Weibull AFT / Cox PH) |
| scikit-learn | 1.5.2 | BSD-3-Clause | ✅ | ML models, calibration, metrics |
| xgboost | 2.1.2 | Apache-2.0 | ✅ | Gradient boosting |
| lightgbm | 4.5.0 | MIT | ✅ | Gradient boosting |
| shap | 0.46.0 | MIT | ✅ | Explainability |
| streamlit | 1.39.0 | Apache-2.0 | ✅ | Dashboard |
| plotly | 5.24.1 | MIT | ✅ | Charts |
| pytest | 8.3.3 | MIT | ✅ | Testing |
| pytest-cov | 5.0.0 | MIT | ✅ | Coverage |
| ruff | 0.7.4 | MIT | ✅ | Lint/format |
| jupyter / nbconvert / ipykernel | 1.1.1 / 7.16.4 / 6.29.5 | BSD-3-Clause | ✅ | Notebook execution (EDA appendix) |

## Phase 7 extras (`requirements-assistant.txt` — installed only when Phase 7 begins)

| Package | Version | Licence | OSI? | Purpose |
|---|---|---|---|---|
| ollama (Python client) | 0.3.3 | MIT | ✅ | Local LLM inference client |
| sentence-transformers | 3.2.1 | Apache-2.0 | ✅ | Embeddings for retrieval |
| torch | 2.14.0+cpu | Apache-2.0 (+ BSD/MIT/BSL components) | ✅ | sentence-transformers' backend. **Must be installed as the explicit CPU-only build** (`--index-url https://download.pytorch.org/whl/cpu`) on this machine — the default PyPI wheel is CUDA-enabled and its DLL layout conflicts with an already-imported pandas/numpy in the same process (`OSError: [WinError 1114] ... c10.dll`, found during Phase 7 build; not a licensing issue, see HANDOFF.md and `requirements-assistant.txt`) |
| jinja2 | 3.1.4 | BSD-3-Clause | ✅ | Deterministic fallback templating |

**LLM weights:** **Qwen2.5-7B-Instruct** (Apache-2.0) — pulled via Ollama at
Phase 7. **Mistral-7B-Instruct** (Apache-2.0) is the documented fallback if
Qwen2.5 is unavailable on the demo machine.

## Rejected, with reasons

| Candidate | Reason rejected |
|---|---|
| **Llama 3.x (any size)** | Meta's Llama Community Licence is **not OSI-approved** (use restrictions + a monthly-active-user clause). Violates the project's explicit open-source-only constraint. Replaced with Qwen2.5-7B-Instruct (Apache-2.0). |
| **chromadb** | Its `chroma-hnswlib` dependency requires compiling a native C++ extension; this build machine has no MSVC Build Tools installed, and requiring one is a fragile, avoidable demo-day dependency. Replaced with a brute-force numpy cosine-similarity search over the ~2,000-project narrative corpus (small enough that no vector index is needed) — see HANDOFF.md Phase 1 report. |
| **OpenAI / Anthropic / Google / Cohere / Groq / any hosted inference API** | Paid or hosted; violates the open-source-only, fully-offline constraint (PRD §3.2) regardless of free-tier availability. |
| **Prophet / deep time-series networks** | Not a licensing rejection — a fit rejection. This is tabular panel data over ~2,000 entities; gradient boosting is the appropriate tool (PRD §3.2). |
| **React / Next.js** | Not a licensing rejection — a scope rejection. Would consume build time on frontend plumbing better spent on modelling rigour (PRD §3.2). |

## How to audit a new dependency before adding it

1. Check `pip show <package>` or the project's `LICENSE` file for the licence identifier.
2. Cross-reference against the [OSI-approved licence list](https://opensource.org/licenses).
3. Add a row to the appropriate table above (core or Phase-7-extras).
4. If not OSI-approved: do not add it. Find an alternative, or raise it with the user.

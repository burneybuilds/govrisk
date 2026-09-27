# GovRisk — SIH TECHNICAL APPROACH

**GovRisk = AI-driven early-warning & risk-intelligence system for government infrastructure projects** (rule-engine + deterministic statistical AI + optional LLM, bilingual React dashboard, India risk map). All claims verified against actual code in `backend/` and `frontend/`, labeled **[IMPLEMENTED]** / **[PARTIAL]** / **[PLANNED]** .

---

## 1. Technology Stack

| Layer | Tech (verified) | Status |
|---|---|---|
| Frontend | React 19, TypeScript ~6.0, Vite 8, Tailwind CSS 4, react-router 7, React-Leaflet 5 + Leaflet 1.9, Recharts 3, TanStack React Query 5, Zod 4, lucide-react, Vitest | [IMPLEMENTED] |
| Backend | Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2 ORM, Pydantic v2, python-jose (JWT), bcrypt, python-dotenv | [IMPLEMENTED] |
| Data | SQLite ×2 (`auth.db` + `govrisk.db`), GeoJSON (local `public/data`), CSV import | [IMPLEMENTED] |
| AI/ML | Deterministic statistical engine (pure stdlib `math`), keyword-pattern NLP, provider-agnostic LLM adapter | [IMPLEMENTED] / [PARTIAL] |
| Monitoring/observability | `/api/health` endpoint | [IMPLEMENTED] |

Note (verified): `requirements.txt` has **only 8 packages — no sklearn/torch/pandas/numpy**. This is intentional: risk scoring is fully deterministic and auditable, not a black box.

---

## 2. System Architecture (2-tier)

```
[React SPA (Vite, Tailwind)
   Pages: Dashboard · Projects · Risk Map · Analytics
          Alerts · Assistant · Reports · Settings · Admin
   Hooks: React Query   Layers: Leaflet + GeoJSON   i18n: EN+HI]
        │  apiFetch + JWT refresh queue
        ▼
[FastAPI REST (10 routers: auth/users/admin/projects/alerts/
   dashboard/analytics/risk_map/assistant/ai) + CORS allowlist]
        ▼
[Service layer: risk_service · project_service]
        ▼
[AI package: predictor · feature_engineering · anomaly_detector ·
   emerging_risk · llm_service · ai_service (cached snapshots)]
        ▼
[ ingest pipeline: data.gov.in / CSV → validate → normalize →
   dedup → upsert → provenance ledger ]
        ▼
[SQLite: govrisk.db (domain)  ·  auth.db (users + audit)]
```

Data flow direction: **Frontend ⇄ FastAPI ⇄ Services ⇄ (AI package | Ingest) ⇄ DBs**. AI snapshots are written to tables (`ai_predictions`, `ai_anomalies`, `ai_emerging_risks`, `ai_analyses`) and *pulled* by dashboard/assistant from the same DB — no live model calls per view (6-h TTL). **[IMPLEMENTED]**

---

## 3. Implementation Methodology

1. **Demo-first data** — `backend/seed.py` builds `govrisk.db` from `seed_data.py`: **6 real-looking demo projects** (NH-48, Eastern Dedicated Freight Corridor, etc.), **10 alerts**, **40 narrative project updates**, and structured `risk_inputs` for all 6. Seed then immediately runs the AI snapshot per project so early-warnings appear on first load. **[IMPLEMENTED]**
2. **Deterministic rule engine first** — `services/risk_service.py` explicitly states *"NO LLM / NO ML"* for the base Risk Score: transparent, reproducible, fully explainable. **[IMPLEMENTED]**
3. **Deterministic statistical + NLP AI layer** — trend extrapolation, keyword polarity, threshold anomalies, emerging-risk taxonomy; optional LLM enrichment only when env-configured. **[IMPLEMENTED]** / **[PARTIAL - LLM off by default]**
4. **Two databases** — domain vs. auth split for security isolation. **[IMPLEMENTED]**
5. **Progressive frontend scope** — Dashboard → Map layers → Analytics → AI Assistant → Admin panel → i18n. **[IMPLEMENTED]**

---

## 4. AI/ML Pipeline

Honest framing for judges: *no trained ML models are shipped*; the AI subsystem is a **deterministic statistical + NLP early-warning engine with an optional LLM layer**. Stages (all verified in `backend/ai/`):

1. **Inputs** — `projects` (progress, cost, dates, milestones, `risk_inputs`) + `project_updates` (free text).
2. **Feature engineering** (`feature_engineering.py`) — keyword-polarity scoring of each update text within **−1…1**, plus risk-key-term extraction (delay/funding/land/contractor terms).
3. **90-day predictor** (`predictor.py`) — extrapolates progress velocity/slippage over a 90-day horizon; sigmoid-normalized probabilities for **schedule_delay, cost_overrun, risk_escalation, clearance_delay, contractor_failure**; `expected_delay_months` range; `prediction_confidence` + `data_points_used`; blend of numerical trend + text polarity (**text weight 0.4**); `future_score` vs `current_score`; `top_drivers`; `model_version = govrisk-ai-v1`; method = `rule_statistical_fallback` | `hybrid`. **[IMPLEMENTED]**
4. **Anomaly detection** (`anomaly_detector.py`) — threshold-based deviation checks (schedule slippage, cost overrun, stalled updates, milestone delays) → `HIGH/MEDIUM/LOW` severity + evidence strings; table `ai_anomalies`. **[IMPLEMENTED]**
5. **Emerging-risk extraction** (`emerging_risk.py`) — keyword taxonomy across **14 categories** (STAKEHOLDER_CONFLICT, COMMUNITY_OPPOSITION, CONTRACTOR_DISPUTE, DESIGN_CHANGE, PROCUREMENT_DISRUPTION, RESOURCE_SHORTAGE, REGULATORY_CHANGE, LAND_ACQUISITION, INTER_DEPARTMENT_COORDINATION, FUNDING_ISSUE, TECHNICAL_COMPLEXITY, ENVIRONMENTAL_CONCERN, POLITICAL_OR_ADMINISTRATIVE_DEPENDENCY, OTHER) with confidence/severity/recommended actions; sources from update IDs. **[IMPLEMENTED]**
6. **Orchestration + caching** (`ai_service.py`) — `analyze_project()` runs all modules, persists snapshots; **6-h TTL cache**, **168-h alert dedup**, background re-analysis via FastAPI `BackgroundTasks` on project/update creation; `latest_prediction`/`_active_emerging_risks`/`_recent_anomalies` feed Assistant + Dashboard. **[IMPLEMENTED]**
7. **Optional LLM layer** (`llm_service.py` + `prompts.py`) — OpenAI-compatible `/chat/completions` *and* Anthropic Messages, via stdlib `urllib`, JSON extraction from response, bounded timeout (30 s) + retries, **never raises** (falls back silently). Triggered only if `AI_PROVIDER`/`AI_API_KEY` set. **[PARTIAL]**

Output contract surfaced in the frontend `AiInsights` type: `prediction`, `anomalies[]`, `emerging_risks[]`, `explanation`, `ai_available`, `analysis_kind: cached|fresh`. **[IMPLEMENTED]**

---

## 5. Risk Factors

15 core factors with configured weights totalling **100** (`services/risk_config.py`, verified):

> **budget 10 · schedule 12 · completion 8 · financial 10 · weather 5 · ground 6 · calamity 5 · material 7 · workforce 6 · contractor 8 · engineering 7 · clearance 5 · administrative 5 · supply_chain 4 · legal_social 2**

- **Risk Score** = round(clamp(Σ probability×impact over weighted factors, 0, 1) × 100) → mapped to **LOW / MEDIUM / HIGH / CRITICAL** bands.
- **Missing-data handling** — neutral baseline probabilities + reduced `risk_confidence`, so incomplete records still score honestly.
- **Interaction penalties** (e.g., weather×ground, schedule×contractor) and **critical overrides** escalate combined exposure.
- Inputs per factor come from structured `risk_inputs` (weather condition/disruption, land acquired %, pending approvals, contractor milestone misses, rework, supply dependency, etc.) plus derived project-level probabilities (`delay_probability`, `cost_overrun_probability`, `implementation_risk`).
- `risk_report`/`risk_factors`/`recommendations` are generated text for explainability. **[ALL IMPLEMENTED]**

---

## 6. Backend Architecture

- **`main.py`** — creates FastAPI app, registers **10 routers**, CORS allowlist (`localhost:5173/5174/127.0.0.1:5173`), `/api/health`. **[IMPLEMENTED]**
- **Routers** — `auth` (register/login/refresh/logout/me), `users` (profile, password, role/status CRUD, stats, reset-password), `admin` (audit-logs + ingest-audit, `require_admin`), `projects` (CRUD, `/risk`, updates CRUD), `alerts`, `dashboard`, `analytics` (riskByState, riskTrends, topRiskFactors), `risk_map`, `assistant` (rule-first reply + appended AI early-warning note), `ai` (health, prediction, anomalies, emerging-risks, explanation, insights, analyze, resolve). **[IMPLEMENTED]**
- **Services** — `risk_service.py` (assessment, analytics, `generate_assistant_response`), `project_service.py` (ID gen `PRJ-###`/`ALR-###`, planned-progress-from-dates, alert auto-creation). **[IMPLEMENTED]**
- **Auth prefix** — `auth/` package: security (bcrypt+JWT), dependencies (guards), models (User + AuditLog), schemas, serializers, `audit.py`. **[IMPLEMENTED]**
- **Ingest** — `ingest/` package + CLI `python -m ingest.run --source data_gov_in|csv_file --dry-run`: fetch → parse → validate → normalize → **deduplicate (by `external_ref`)** → upsert → audit. Adapters: `sources/data_gov_in.py` (api.data.gov.in) and `sources/csv_file.py` (column map for `data/sample_projects.csv`). **[IMPLEMENTED]**
- **Migration & seed** — `migration.py` (idempotent ADD-COLUMN / CREATE-TABLE), `seed.py`/`seed_auth.py`. **[IMPLEMENTED]**
- **Tests** — `tests/` has 3 modules: `test_ai_analysis.py`, `test_ingest.py`, `test_risk_service.py`. **[IMPLEMENTED]**

---

## 7. Frontend Architecture

- **12 pages** — Login, Register, Dashboard, Projects, ProjectDetails, RiskMap, Analytics, Alerts, Assistant, Reports, Settings, AdminPanel. **[IMPLEMENTED]**
- **Shell** — `AppLayout` (Sidebar + Topbar + `LanguageSwitcher`); `ProtectedRoute`/`AdminRoute` route guards; `AuthContext` (me-on-mount, logout). **[IMPLEMENTED]**
- **Dashboard** — KPI cards, sector filter chips, high-risk table (cost-overrun %, delay %, RiskScore), **AI Early-Warning cards** (future risk score, delay/cost probabilities, anomaly & emerging-risk chips). **[IMPLEMENTED]**
- **Risk Map** (`components/map/`) — Leaflet, CartoDB Positron tiles (optional authenticated key), project markers shaded by **Okabe-Ito colorblind-safe** risk palette, region **choropleths** (Composite Risk, Disaster History), **Live Weather overlay**, Region/Project detail panels, LayerControlPanel, MapLegend, MapStatusBanner; **lazy district boundaries at zoom ≥ 7**; viewport debounce. **[IMPLEMENTED]**
- **Data layer** — React Query hooks with per-source `staleTime`/`retry` + exponential backoff; Zod validation of external payloads; weather/disaster fetchers **env-overridable with built-in fixtures** (8 s timeout). **[IMPLEMENTED]**
- **Charts** — Recharts: RiskChart (distribution), RiskTrendChart (sector-filterable), RiskFactorChart. **[IMPLEMENTED]**
- **Assistant page** — monitored-projects table + `AIChat` component (suggested questions, typing state) calling `/api/assistant`. **[IMPLEMENTED]**
- **i18n** — full EN + Hindi strings, `useI18n`, language switcher. **[IMPLEMENTED]**
- **API client** — `services/api.ts`: token storage + **single-flight token refresh** on 401, structured error messages. **[IMPLEMENTED]**
- **Tests** — `src/test/setup.ts` only → unit tests **[PLANNED]**. Lint/typecheck tooling available (oxlint, Vitest). **[VERIFIED PRESENT]**

---

## 8. Database Architecture

- **`govrisk.db`** (domain, SQLite via SQLAlchemy):
  - `projects` — full infra-project record incl. `risk_inputs`, `risk_factors`, `recommendations` (JSON text), `risk_confidence`, `risk_report`, geo lat/lng, milestone counts, **ingest-provenance columns** (`status`, `scale`, `funding_source`, `external_ref`, `source_name`, `source_url`, `retrieved_date`, `data_confidence`, `last_synced_at`).
  - `alerts`, `project_updates` (free-text source for AI).
  - `ai_analyses` (run history/cache), `ai_predictions` (latest 90-day snapshot), `ai_anomalies`, `ai_emerging_risks` (with `resolved`/`status`, evidence + recommendations JSON, `source_update_ids`).
  - `ingest_audit_log` — **append-only provenance** (`INSERT|UPDATE|SKIP|MERGE|REJECT`), no deletes.
  - Composite indexes on `(project_id, created_at)`. **[ALL IMPLEMENTED]**
- **`auth.db`** — `users` (role, department, active, last_login, password_hash), `audit_logs`. **[IMPLEMENTED]**
- **Schema evolution** — idempotent `migration.py` (adds district/description/status/scale/funding + AI tables). **[IMPLEMENTED]**

---

## 9. Security Architecture

- **bcrypt** password hashing; **JWT HS256** access token (**30 min**) + refresh token (**7 days**) with `sub/role/type/exp/iat` claims; refresh rotation on renewal. **[IMPLEMENTED]**
- **HTTPBearer** + `get_current_user` / `get_current_active_user` / `require_admin` / `require_roles` guards; RBAC roles `admin | officer | analyst | viewer`; self-registered users default to `viewer`. **[IMPLEMENTED]**
- **Audit logging** — login success/fail, user/project create-update, role changes (both auth audit-logs and ingest ledger). **[IMPLEMENTED]**
- **CORS allowlist** (localhost only). **[IMPLEMENTED]**
- **Split-storage isolation** — domain vs. auth DBs; secrets via `.env` (`backend/.env` contains real keys — never committed/exposed; `.env.example` documents all). **[IMPLEMENTED]**
- **Frontend tokens in localStorage** *[PARTIAL — httpOnly-cookie session is the hardening path]*; **no rate-limiting / account-lockout** *[PLANNED]*.

---

## 10. External APIs / Data Sources

- **data.gov.in API** — adapter implemented; needs `DATA_GOV_IN_API_KEY` + `DATA_GOV_IN_RESOURCE_ID`, off by default. **[PARTIAL]**
- **CSV ingest** — `backend/data/sample_projects.csv` works end-to-end. **[IMPLEMENTED]**
- **India GeoJSON** — states + districts shipped in `frontend/public/data`, fetched lazily. **[IMPLEMENTED]**
- **Basemap** — CartoDB Positron tiles (public CDN + optional `VITE_TILE_API_KEY`). **[IMPLEMENTED]**
- **Weather & disaster feeds** — `VITE_WEATHER_API_URL`/`VITE_DISASTER_API_URL` pluggable; **fixtures used by default** with zod validation + adapters. **[PARTIAL]**
- **LLM providers** — OpenAI-compatible + Anthropic Messages adapters, off unless configured. **[PARTIAL]**

---

## 11. Deployment

- **[PLANNED / LOCAL ONLY]** — verified: **no Dockerfile, no docker-compose, no CI/CD (`.github` absent), no vercel/netlify/render configs.** Run is manual: `uvicorn main:app` + `npm run dev/build` with file-based SQLite. Slide must say *"local demo build; production path: containerize API → managed database → hosted geodata+map tiles → SSO."*
- **[PLANNED]** — hosting, TLS, secrets management, backups, horizontal scaling.

---

## 12. End-to-End Workflow

```
1. Auth: user logs in (JWT access+refresh, bcrypt, ROLES).
2. Ingest: data.gov.in / CSV → ingest pipeline → validate → normalize →
   dedup → upsert → provenance ledger → govrisk.db.  (seeded demo for SIH)
3. Risk engine scores every project (15 weighted factors) → risk_level,
   delay/cost probabilities, auto-alerts.
4. AI analysis (creation/update-triggered + on-demand): 90-day prediction,
   anomalies, emerging risks → persisted snapshots (6-h TTL).
5. User opens Dashboard → KPIs, high-risk table, AI early-warning cards.
6. Drills into Project Details → updates feed, risk breakdown, recommendations.
7. Risk Map → project markers + state/district choropleths + live weather.
8. Analytics → trends, top risk factors; Alerts → triage screen.
9. Officer posts a project update → backend re-analyzes in background →
   new anomaly/emerging-risk surfaces.
10. Admin panel → user lifecycle + audit-logs; Assistant → Q&A with live
    AI early-warning context appended to the deterministic answer.
```

---

## 13. Technical Highlights (pick-your-ammo)

- **Deterministic + explainable** risk scoring by design (no black-box), 15 configurable weighted factors.
- **Transparent 90-day AI early-warning** lifecycle: {predictions, anomalies, emerging risks} cached & versioned (`govrisk-ai-v1`).
- **Provider-agnostic LLM adapter** with graceful zero-config fallback — AI works with **zero environment keys**.
- **Append-only audit + provenance ledger** (ingest and auth) — full traceability story (great for governance).
- **Split-domain DBs** (`auth.db` vs `govrisk.db`) — defense-in-depth talking point.
- **Free-text intelligence** — project updates drive anomaly/emerging-risk detection (NLP keyword polarity).
- **Bilingual (EN + Hindi) React SPA + India map** with colorblind-safe choropleths and lazy district boundaries.
- **No heavy ML stack** — the entire AI subsystem runs on stdlib; easy to run anywhere, easy to verify.
- **Idempotent migrations + seed-first demo** so the map, dashboard and assistant are alive on first boot.

---

## 14. EXACT CONTENT FOR SIH PPT (slide bullets)

**Title slide:** "GOVRISK — AI Early-Warning System for Government Infrastructure Projects" (Smart India Hackathon 2026)

**Problem:** Delayed/cost-overrun public projects have no transparent, real-time risk early-warning.

**Our answer in three lines:**
- One rule-based + AI risk intelligence engine: **scored** projects → **predicted** 90-day outlook → **detected** anomalies & emerging risks → **prescribed** actions.
- Full-stack bilingual (EN+HI) dashboard with an **India risk map** for ministries/PSUs/district officials.
- Works with **zero ML dependencies** and **zero external keys** out of the box (LLM optional).

**Key numbers to quote:**
- 15 configurable risk factors; risk horizon **90 days**; prediction refresh cache **6 h**; alert dedup window **168 h**; **5** probability outputs per project; **14** emerging-risk categories; **30-min access / 7-day refresh** JWT; **2** split databases; **6** demo projects / **10** alerts / **40** narrative updates seeded; **12** frontend pages; **3** backend test modules.

**Architecture (5 boxes):**
`Data sources (data.gov.in / CSV)` → `Ingest+validate+dedup+audit` → `Risk engine & AI early-warning (deterministic + optional LLM)` → `FastAPI REST + SQLite (govrisk.db | auth.db)` → `React dashboard + Leaflet risk map`.

**AI pipeline (show as 6-step):**
`Project data + officer updates` → `Keyword polarity features` → `90-day statistical prediction (delay/cost/escalation/clearance/contractor)` → `Anomaly detection` → `Emerging-risk extraction (14 categories)` → `Cached AI snapshot → dashboard + assistant`.

**Security:** bcrypt + JWT refresh rotation + RBAC (admin/officer/analyst/viewer) + full audit logs + split DBs + CORS allowlist.

**Scope honesty box:** Implemented = everything above; Partial = live weather/disaster feeds (fixtures), live LLM (off), live data.gov.in fetch (key-gated); Planned = containerization, CI/CD, rate-limiting, SSO, ML training.

---

## 15. EXACT FLOWCHART TO DRAW

```
┌──────────────────────────────────────────────────────────────────────┐
│  SOURCES                                                             │
│   data.gov.in API ──┐           officer free-text updates ──┐        │
│   CSV bulk import ──┤────────► [ ══ ]────────────────────────┤        │
│   (GeoJSON local)   ┘                     │                         │
└──────────────────────────────────────────────┬─────────────────────────┘
                                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  INGEST PIPELINE  fetch → parse → validate → normalize →             │
│                   dedupe(external_ref) → upsert → audit ledger       │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  RISK INTELLIGENCE                                                    │
│  ┌────────────────────┐  ┌──────────────────────────────────────────┐ │
│  │ RULE ENGINE        │  │ AI LAYER (deterministic, optional LLM)   │ │
│  │ 15 factors, weights│  │  polarity → 90-day prediction (5 probs)  │ │
│  │ inter. penalties,  │  │  → anomalies → emerging risks (14 cat.)  │ │
│  │ overrides          │  │  → cached snapshot (TTL 6h)              │ │
│  └────────────────────┘  └──────────────────────────────────────────┘ │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BACKEND  FastAPI routers (auth/users/admin/projects/alerts/         │
│           dashboard/analytics/risk_map/assistant/ai) — JWT+RBAC      │
│           DBs: govrisk.db  |  auth.db (audit logs)                   │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FRONTEND  React + Leaflet:  Dashboard (KPIs + AI early-warnings) → │
│  Risk Map (markers + choropleths + weather) → Project Detail →       │
│  Analytics/Alerts → AI Assistant (EN+HI) → Admin                       │
└──────────────────────────────────────────────────────────────────────┘
```

(Fork after "sources": numerical project data vs. officer text updates; converge at Risk Intelligence.)

---

## 16. WHAT TO PUT ON THE SLIDE (10-min layout)

- **Slide 1 (minute 0–1):** Title + problem statement + 3-line solution + demo accounts.
- **Slide 2 (minute 1–3):** the 5-box architecture from §14 — LEFT layering, big arrows.
- **Slide 3 (minute 3–5):** the AI pipeline 6-step flow with the 5 probability outputs + 14 emerging-risk categories + the "zero dependencies / works offline" badge.
- **Slide 4 (minute 5–7):** **Live demo** — Dashboard (early-warning cards) → Risk Map (choropleth + weather overlay) → one Project Detail → Assistant Q&A; toggle EN/Hindi.
- **Slide 5 (minute 7–9):** Security (JWT refresh + RBAC + audit + split DBs) + ingest provenance ledger.
- **Slide 6 (minute 9–10):** Impact & honesty — what's IMPLEMENTED vs PARTIAL vs PLANNED, why deterministic-AI-first is a governance feature. End on "portable, auditable, bilingual, API-ready."

---

## 17. IMPLEMENTED vs PARTIAL vs PLANNED

**IMPLEMENTED (verified in code)**
- Full CRUD APIs (10 routers); JWT access+refresh, bcrypt, RBAC (admin/officer/analyst/viewer), audit logs, admin user lifecycle + reset-password.
- Deterministic risk engine (15 weighted factors, penalties, overrides, confidence) + auto-alert generation + `risk_report`.
- AI early-warning: 90-day prediction (5 probabilities, delay range, confidence, drivers, `govrisk-ai-v1`), anomaly detection, 14-category emerging-risk extraction, explainability; TTL cache + dedup + background re-analysis.
- Hybrid Assistant (rule-first replies + live AI context), bilingual UI, 12-page dashboard, India risk map (markers, risk & disaster choropleths, weather overlay, layer controls, lazy districts), analytics/charts, Geolocation markers.
- CSV + data.gov.in adapters, normalize/dedupe, ingest provenance ledger, canonical sectors/states.
- Split DBs, idempotent migrations, seeds (6 projects/10 alerts/40 updates), backend test suite (3 modules), `/api/health`.

**PARTIAL**
- **Live weather/disaster data** — pluggable env URLs exist but fixtures ship by default.
- **LLM enrichment** — adapter implemented (OpenAI-compatible + Anthropic) but off without env keys; deterministic path is the default.
- **Live data.gov.in fetch** — adapter present, key-gated, disabled by default (CSV demo used).
- **Frontend testing** — Vitest scaffolded (`src/test/setup.ts`) but no unit tests written.
- **Session hardening** — tokens live in localStorage (workable; httpOnly-cookie is the upgrade).

**PLANNED**
- Containerization (Dockerfiles), CI/CD (`.github` absent), cloud deployment, managed DB, TLS/secrets manager, backups.
- Rate-limiting & account lockout on auth endpoints.
- Full supervised ML training run (once live labelled portfolio data is available) to replace/augment deterministic estimation.
- ML-driven delay/classification fine-tuning + production data.gov.in integration.
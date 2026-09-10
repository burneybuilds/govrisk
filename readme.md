# GovRisk — AI-Powered Infrastructure Risk Intelligence Platform

A web application for monitoring government infrastructure projects, identifying risk early, and empowering officials with AI-driven insights. Built for the Smart India Hackathon 2026.

## Architecture

```
React Frontend (Vite + TypeScript)
      |
      | JWT authentication (Bearer token)
      v
FastAPI Backend
      |
      +----------------------+
      |                      |
      v                      v
   auth.db                govrisk.db
      |                      |
    users                projects
                         alerts
```

### Why two databases?

- **`auth.db`** — Authentication data (users, password hashes, roles). Kept separate so security-critical data is isolated from project data and can be backed up, migrated, or replaced independently.
- **`govrisk.db`** — Domain data (projects and alerts) that powers the risk monitoring product.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4, React Router, Leaflet |
| Backend | FastAPI, SQLAlchemy 2 |
| Databases | SQLite (`auth.db` + `govrisk.db`) |
| Auth | JWT (access + refresh tokens), bcrypt password hashing |

## Roles

| Role | Capabilities |
|---|---|
| `admin` | All access + User Management (create/disable users, change roles) |
| `officer` | Project monitoring, analytics, reports |
| `analyst` | Project monitoring, analytics, AI assistant |
| `viewer` | Read-only access to the platform (default for new registrations) |

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@govrisk.gov.in` | `admin123` |
| Officer | `officer@govrisk.gov.in` | `officer123` |
| Analyst | `analyst@govrisk.gov.in` | `analyst123` |
| Viewer | `viewer@govrisk.gov.in` | `viewer123` |

> These are DEMO credentials only. Never use default secrets in production.

## Backend Setup

```bash
cd backend

# Install dependencies (uses Python 3.13)
pip install -r requirements.txt

# Seed the project database (govrisk.db)
python seed.py

# Seed the authentication database (auth.db) — idempotent, safe to rerun
python seed_auth.py

# Run the API server
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

## Environment Variables

Backend reads configuration from `backend/.env` (see `backend/.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./govrisk.db` | Project monitoring database |
| `AUTH_DATABASE_URL` | `sqlite:///./auth.db` | Authentication database |
| `JWT_SECRET_KEY` | dev value | Secret used to sign JWT tokens — set a strong value in production |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |

Frontend reads `frontend/.env`:

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

## API Endpoints

### Authentication (`auth.db`)

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/api/auth/register` | Create account (always role `viewer`) | Public |
| POST | `/api/auth/login` | Sign in, returns access + refresh tokens | Public |
| POST | `/api/auth/refresh` | Get a new access token | Refresh token |
| POST | `/api/auth/logout` | Log out | Authenticated |
| GET | `/api/auth/me` | Current user details | Authenticated |

### User Profile & Management

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/users/me` | View own profile | Authenticated |
| PUT | `/api/users/me` | Update own `fullName`, `department`, `designation` | Authenticated |
| PUT | `/api/users/me/password` | Change own password | Authenticated |
| GET | `/api/users` | List all users | Admin |
| GET | `/api/users/{id}` | Get user by ID | Admin |
| PUT | `/api/users/{id}` | Update user | Admin |
| PATCH | `/api/users/{id}/role` | Change user role | Admin |
| PATCH | `/api/users/{id}/status` | Activate/deactivate user | Admin |

### Project Monitoring (`govrisk.db`)

All endpoints below require a valid JWT (returns `401` otherwise).

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/projects` | List all projects |
| GET | `/api/projects/{id}` | Project details |
| GET | `/api/alerts` | List early-warning alerts |
| GET | `/api/dashboard` | Portfolio KPIs + high-risk table |
| GET | `/api/analytics` | Sector analytics + risk matrix |
| GET | `/api/risk-map` | Geo data for the risk map |
| POST | `/api/assistant` | AI assistant query |
| GET | `/api/health` | Health check (public) |

## Authentication Flow

1. User signs in → backend verifies password (bcrypt) → issues **access token** (JWT, 30 min) + **refresh token** (JWT, 7 days)
2. Frontend stores tokens and attaches `Authorization: Bearer <accessToken>` to every request
3. On `401`, the frontend automatically refreshes the access token using the refresh token
4. Backend validates the JWT and checks the user's role before serving data
5. Logout clears token state client-side

## Security Notes

- Passwords are hashed with **bcrypt** — never stored or returned in plaintext
- Email has a unique index — duplicate account creation is rejected with `409`
- Scope limits authorization server-side: even if a non-admin manually calls `/api/users`, they receive `403`
- HTTP status codes: `401` unauthenticated, `403` authenticated but not authorized, `404` not found, `409` conflict, `422` validation
- The last remaining active admin cannot be deactivated or demoted

## HTTP Status Codes

| Code | Meaning |
|---|---|
| 401 | Unauthenticated — missing/expired/invalid token or bad credentials |
| 403 | Authenticated but role not permitted |
| 404 | Resource does not exist |
| 409 | Duplicate/conflict (e.g. email already registered) |
| 422 | Request validation failed |

## Project Structure

```
backend/
├── auth/
│   ├── database.py        # auth.db engine + session
│   ├── models.py          # User model
│   ├── schemas.py         # Pydantic auth schemas
│   ├── security.py        # bcrypt hashing + JWT create/verify
│   └── dependencies.py    # get_current_user, require_admin, require_roles
├── routers/
│   ├── auth.py            # register / login / refresh / logout / me
│   ├── users.py           # profile + password + admin user management
│   ├── projects.py
│   ├── alerts.py
│   ├── dashboard.py
│   ├── analytics.py
│   ├── risk_map.py
│   └── assistant.py
├── services/risk_service.py
├── database.py            # govrisk.db engine + session
├── models.py              # Project + Alert models
├── schemas.py
├── seed.py                # seeds govrisk.db
├── seed_auth.py           # seeds auth.db (idempotent)
├── main.py                # FastAPI app + CORS + routers
├── govrisk.db
├── auth.db
└── .env / .env.example

frontend/
├── src/
│   ├── context/AuthContext.tsx   # auth state (user, login/logout, loading)
│   ├── components/
│   │   ├── auth/ProtectedRoute.tsx
│   │   └── layout/               # Sidebar, Topbar, AppLayout
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Projects.tsx
│   │   ├── ProjectDetails.tsx
│   │   ├── RiskMap.tsx
│   │   ├── Analytics.tsx
│   │   ├── Alerts.tsx
│   │   ├── Assistant.tsx
│   │   ├── Reports.tsx
│   │   └── Settings.tsx
│   └── services/api.ts           # centralized API helper (auto Bearer token)
```

## Production Readiness

This is an SIH MVP. Before production, consider:

- Strong `JWT_SECRET_KEY` via environment/config secrets
- PostgreSQL instead of SQLite
- Rate limiting on auth endpoints
- Email verification & password reset flows
- Refresh-token rotation with revocation
- OAuth/SSO, MFA, OTP as required by enterprise policy
>>>>>>> eb63de5a6db0b315f767d73e66d02cf053cef1e6

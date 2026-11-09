# Autolancer – Prototype Phase 1

A working slice of Autolancer covering the nine Phase 1 rows of
`Requirements/prototype_requirements.docx` (UC-001 and UC-002): sign-in, the
Marketplace Simulator connection, the owner profile and AI profile draft, the versioned
autonomy policy, job discovery, AI assessment within a daily spending cap, rule-based
classification and ranking, and the ranked job feed.

```
phase1/
├── README.md        this file
├── supabase.sql     row-level security (owner-only policies) for the six tables
├── api/             FastAPI + SQLAlchemy + Pydantic + LiteLLM (Python 3.13)
│   ├── app/         routers, services, rules, LLM gateway, auth, models
│   ├── simulator/   Marketplace Simulator sub-app (mounted at /sim) + jobs.json
│   └── tests/       pytest, one file per Phase 1 row
└── hub/             Next.js 16 (App Router) + TypeScript + Tailwind 4, client components
```

## How it fits together

```
Browser (hub) ──Supabase JS──▶ Supabase Auth            (email/password sign-in only)
      │
      └── Bearer <access token> ──▶ API (FastAPI) ──▶ Postgres (Supabase) / SQLite locally
                                     │  verifies the Supabase JWT, filters every query by owner_id
                                     ├── HTTP (SIMULATOR_URL) ──▶ /sim  Marketplace Simulator
                                     └── LiteLLM (LLM_MODEL)  ──▶ model provider, or "mock"
```

* The simulator runs in the same process as the API (one deploy) but the API reaches it
  only over HTTP through `app/marketplace.py`, so a real marketplace adapter can replace it.
* Tables are created on startup (`create_all`): `profiles`, `policy_versions`,
  `connections`, `listings`, `assessments`, `ai_usage`.

## What each Phase 1 row does and where it lives

| # | Row | Behaviour | Code | Tests |
|---|-----|-----------|------|-------|
| 1 | Sign-in / sign-out | Supabase email/password. Any failure shows one generic message. The API returns the same 401 for every bad token and a 404 for another owner's job. | `hub/src/app/login`, `hub/src/components/AuthGate.tsx`, `api/app/auth.py` | `test_row1_auth.py` |
| 2 | Connections | Turning the simulator on calls `/sim/capabilities`: **connected** + operations, or **unavailable** if the call fails or `list_listings` is missing. Turning it off leaves it **disconnected** and fetch is blocked. | `routers/connections.py`, `hub/.../connections` | `test_row2_connections.py` |
| 3 | Profile | Services (checkboxes), skills summary, evidence (links or text). Each real change creates a new profile version. | `routers/profile.py`, `hub/.../profile` | `test_row3_profile.py` |
| 4 | Draft my profile | One LLM call returns `{draft, claims[], unsupported_claims[]}`. Each claim cites the evidence items (E1, E2, …) behind it, and the API checks those citations: a claim with no real evidence is moved to unsupported (FR-003 AC-1). The draft is kept pending until the owner accepts or ignores it. Failures show the reason, and the cost is still recorded. | `services/profile_ai.py` | `test_row4_profile_draft.py` |
| 5 | Policy | Allowed actions, max bid, daily proposal limit, workload limit, daily AI cap, review conditions, min job budget, excluded keywords and a deadline limit (minimum days to deadline). Each valid save inserts a new `policy_versions` row (newest = active). Invalid values get a 422 and nothing is saved. The full history is shown. | `routers/policy.py`, `schemas.PolicyIn` | `test_row5_policy.py` |
| 6 | Fetch jobs | Filters by min budget and excluded keywords, then upserts on (owner, source, source_id). A changed listing gets a new version. Outages and rate limits (network errors, HTTP 5xx/429) are retried up to 3 attempts with 1 s and 2 s waits; other errors are not retried. If all attempts fail, the old list and "last updated" are kept, and the error and attempt count are shown. | `services/discovery.py` | `test_row6_fetch.py` |
| 7 | Assessment | Every listing without a current assessment is assessed. The AI returns category, fit and reasons, deliverables, effort and price ranges, uncertainty, open questions, assumptions and an expected-return basis. A job is skipped as **unassessed** once today's `ai_usage` total reaches the cap. Each call's cost is recorded. A failed call or invalid JSON also gives **unassessed**, and the job has a Retry button. | `services/assessment.py`, `llm.py` | `test_row7_assessment.py`, `test_llm_gateway.py` |
| 8 | Rules + rank | Python rules give pursue / clarify / decline. The score weights fit 0.35, effort 0.15, deadline 0.15, price 0.20 and certainty 0.15. Each assessment stores the listing, profile and policy versions it used, so any change makes it stale. | `rules.py` | `test_row8_rules.py` |
| 9 | Jobs feed | Sorted by score, with filters, new/changed badges, a side drawer with the AI's reasons, score breakdown and versions, and a pursue-eligible flag. | `services/feed.py`, `hub/src/app/(hub)/page.tsx`, `JobDrawer.tsx` | `test_row9_feed.py` |

### Rules in short (`api/app/rules.py`)

* **decline** if the category is not one of your services, fit < 0.4, the budget is below
  your minimum, an excluded keyword matches, the job is due sooner than the policy's deadline
  limit, or the minimum effort cannot fit before the deadline (6 hours/day).
* **clarify** if there are open questions, uncertainty is high, or fit is below 0.6.
* **pursue** otherwise. It is **pursue-eligible** only if the assessment is current, the
  policy allows `submit_proposals`, the proposal and workload limits are above 0, the lowest
  sensible price is within the max bid, and no review condition applies (high uncertainty,
  finance job, deadline under 3 days).

### Rank score and expected return

Each part is scored 0–1: fit (from the AI), effort (less is better, 0 at 160 hours),
deadline slack, price (expected price relative to your max bid) and certainty (low 1.0,
medium 0.6, high 0.2 uncertainty). The drawer also shows the expected-return basis: the AI's
explanation plus the expected price, hours and implied hourly rate used for ranking.

### Re-assessment

A new listing version, profile version or policy version makes the affected
assessments **stale**. Stale jobs keep their old result, but it is labelled and never
eligible. They are queued and re-assessed by **Fetch jobs** or the **Assess N jobs** button.
If only the policy changed, the earlier AI output is reused and only the rules run again,
so there is no new AI cost (UC-002 A1).

## Run locally

Requirements: Python 3.13, Node 20+ (22 recommended).

### API

```bash
cd api
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults work: SQLite + LLM_MODEL=mock
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API, and http://localhost:8000/sim/listings for the simulator.

You still need a Supabase project for sign-in (see Supabase setup below). Put its
`SUPABASE_URL` (and `SUPABASE_JWT_SECRET` if your project uses the legacy secret) in `api/.env`.

### Hub

```bash
cd hub
npm install
cp .env.example .env.local    # fill in the Supabase URL and anon key
npm run dev                   # http://localhost:3000
```

### Tests

```bash
cd api && . .venv/bin/activate
pytest                                   # in-memory SQLite, mock LLM, no keys needed
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/empty_db pytest   # same suite on Postgres
cd ../hub && npm run lint && npm run build
```

### Simulator chaos controls

Use these to demonstrate the exception paths:

```bash
curl -X POST "http://localhost:8000/sim/chaos/fail-next-fetch?count=1"   # one 503: the retry recovers
curl -X POST "http://localhost:8000/sim/chaos/fail-next-fetch?count=3"   # 3 x 503: the fetch fails, old list kept
curl -X POST http://localhost:8000/sim/chaos/edit-listing/SIM-1001   # budget +20%, description changed
curl -X POST http://localhost:8000/sim/chaos/add-listing             # posts a brand-new job
```

Simulator state lives in memory and resets when the API restarts.

### Schema changes

`create_all` creates missing tables but never adds columns to existing ones. After pulling a
change that adds columns, delete the local SQLite file (`api/autolancer.db`). On a Supabase
database, add the column with `alter table` or drop the six tables and restart the API, then
run `supabase.sql` again.

## Environment variables

### API (`api/.env`, see `api/.env.example`)

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | prod | `sqlite:///./autolancer.db` | SQLAlchemy URL. For Supabase use the **Session pooler** URI with the psycopg driver: `postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres` |
| `SUPABASE_URL` | yes* | – | Used to fetch the JWKS (`/auth/v1/.well-known/jwks.json`) when the project uses asymmetric signing keys |
| `SUPABASE_JWT_SECRET` | yes* | – | Legacy HS256 JWT secret. If set it is used instead of JWKS |
| `SIMULATOR_URL` | yes | `http://localhost:8000/sim` | Where the API reaches the marketplace simulator over HTTP |
| `LLM_MODEL` | yes | `mock` | LiteLLM model name (e.g. `deepseek/deepseek-chat`, `openai/gpt-4o-mini`) or `mock` |
| `LLM_TIMEOUT_SECONDS` | no | `60` | Per-call timeout |
| provider key, e.g. `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` | if not mock | – | Read by LiteLLM for the chosen provider |
| `DEFAULT_DAILY_AI_CAP_USD` | no | `0.50` | AI cap used only before the first policy is saved |
| `CORS_ORIGINS` | yes | `http://localhost:3000` | Comma-separated hub origins allowed to call the API |

\* One of `SUPABASE_JWT_SECRET` or `SUPABASE_URL` must be set, or every request is rejected.

### Hub (`hub/.env.local`, see `hub/.env.example`)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | API base URL, no trailing slash |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon / publishable key (sign-in only) |

`.env` and `.env.local` are gitignored. Never commit real keys.

## Supabase setup

1. Create a project (US East, next to the API).
2. **Authentication → Users → Add user**: create the owner account(s) with email and
   password. There is no sign-up page because the spec assumes the owner account exists.
   Create a second user to try owner isolation.
3. **Project Settings → API**: copy the project URL and anon key (for the hub), plus the JWT
   secret if it is shown (legacy keys). With the newer signing keys, setting `SUPABASE_URL`
   is enough.
4. **Connect → Session pooler**: copy the URI and change `postgresql://` to
   `postgresql+psycopg://` for `DATABASE_URL`.
5. Start the API once so it creates the tables, then run `supabase.sql` in the SQL editor
   to enable row-level security with owner-only policies.

## Deploy

### API on Render

1. **New → Web Service** from this GitHub repo.
2. Root directory: `p07-autolancer/Prototype/phase1/api`. Runtime: Python. Render reads
   `.python-version` (3.13).
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Environment: set `DATABASE_URL`, `SUPABASE_URL` (and/or `SUPABASE_JWT_SECRET`),
   `LLM_MODEL` with its provider key, `SIMULATOR_URL=https://<service>.onrender.com/sim`,
   and `CORS_ORIGINS=https://<your-hub>.vercel.app`.
6. Health check path: `/health`. Then run `supabase.sql` (see above).

Do not use SQLite on Render: its disk is wiped on every deploy. On the free plan the
service sleeps when idle, so the first request after a pause is slow.

### Hub on Vercel

1. **Add New → Project**, import the repo, root directory `p07-autolancer/Prototype/phase1/hub`
   (framework auto-detected as Next.js).
2. Environment variables: `NEXT_PUBLIC_API_URL=https://<service>.onrender.com`,
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
3. Deploy, then make sure the Vercel URL is in the API's `CORS_ORIGINS`.
4. In Supabase **Authentication → URL Configuration**, set the Site URL to the Vercel URL.

## Phase 1 decisions and limits

* Projects and proposals are Phase 2. The workload and daily proposal limits are validated
  and versioned now. In Phase 1 they only affect pursue-eligibility (a limit of 0 means not
  eligible).
* "Today" for the AI cap is the UTC day. Mock calls cost $0.001 each so the cap can be tested.
* Client names, countries and ratings are stored for display but never sent to the model
  (AIR-001 fairness).
* Money is stored as floats for simplicity. MFA, scheduled discovery cycles and live
  marketplaces are outside Phase 1.

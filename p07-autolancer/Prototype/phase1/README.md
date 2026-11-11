# Autolancer Phase 1 prototype

The owner hub for Autolancer, covering prototype rows 1–9: UC-001 (sign in, connect the
Marketplace Simulator, set up a profile, AI profile draft, autonomy policy) and UC-002
(fetch jobs, AI assessment, pursue / clarify / decline ranking, the job feed).

- `api/` – FastAPI service and the Marketplace Simulator (mounted at `/sim`)
- `hub/` – Next.js owner hub
- `dev/local_auth.py` – local stand-in for Supabase Auth (development only, never deploy)
- `supabase.sql` – row-level security, run once in Supabase after the API's first start

## How this version came about

This branch is the result of an audit that Huzayfah Abid and Claude (Anthropic's AI
assistant) did together on 11 November 2026. We checked the prototype against
`Requirements/prototype_requirements.docx`, ran it locally, walked both use cases through
in a browser, reviewed the screenshots, and fixed what we found.

### What we fixed and changed

- **Sign-in form kept credentials.** After sign-out the previous owner's email and
  password were still in the form. The form is now cleared when it is hidden and after a
  failed sign-in.
- **Edits could be overwritten.** Returning to the Policy or Profile page showed the old
  form while a reload was in flight, and the reload could replace what was being typed.
  Pages now drop their loaded data and old messages when hidden.
- **Re-assessment after a change (row 8).** A profile or policy change only marked jobs
  stale. The hub now re-assesses the affected jobs straight away and reports the result.
- **Unreachable simulator.** It was reported as "not connected"; it is now reported as
  "unavailable", and Fetch jobs is disabled until the simulator is connected and a policy
  exists.
- **Closed listings.** The fetch result now counts listings the marketplace no longer
  returns, and the simulator has `/chaos/remove-listing/{id}` to demonstrate it.
- **Smaller fixes.** One fetch-failure warning instead of two; the mock AI's hourly rate
  now matches the ranking basis; field labels in policy errors; one-decimal scores; a
  full-width policy history; a plain-language reason when the marketplace is unreachable.
- **Added.** `dev/local_auth.py`, and `api/tests/test_walkthrough_fixes.py` for the API
  changes above.

### What was verified

- 109 API tests pass on SQLite and on Postgres 16.
- A browser walkthrough of both use cases (38 screenshots) completes on both databases
  with no page errors or server errors.
- Not verified: a real Supabase project, a hosted deployment, and a real AI model (the AI
  ran in `mock` mode).

## Run it locally

```bash
cd api
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # then set SUPABASE_URL= (empty) and
                        # SUPABASE_JWT_SECRET=local-dev-secret-0123456789abcdef-0123456789
.venv/bin/uvicorn app.main:app --port 8000 &
SUPABASE_JWT_SECRET=local-dev-secret-0123456789abcdef-0123456789 \
  .venv/bin/uvicorn local_auth:app --app-dir ../dev --port 9999 &

cd ../hub
cp .env.example .env.local   # then set NEXT_PUBLIC_SUPABASE_URL=http://localhost:9999
npm ci && npm run build && npm run start
```

Open http://localhost:3000 and sign in as `owner@example.com` / `owner-pass-123`.
Tests: `.venv/bin/python -m pytest` in `api/`.

Every environment variable is described in `api/.env.example` and `hub/.env.example`.

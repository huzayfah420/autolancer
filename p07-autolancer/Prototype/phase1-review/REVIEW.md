# Autolancer review: requirements, architecture and Phase 1 prototype

Reviewed on 2026-11-10 against the goal of an automatic freelancer that hunts for work,
builds it and deals with the outside world on its own.

The `.docx` files were not edited. The fixes in Part C were first made in a separate copy
of the prototype and have since been ported into `Prototype/phase1/`; the copy was then
removed, so this folder now holds only this review. Part D lists the changed files.

## Documents and precedence

| Short name | File | Date | What it holds |
|---|---|---|---|
| **FR doc** | `Requirements/system_requirements.docx` | 8 Oct | FR-001 to FR-031, AIR-001 to 006, NFR-001 to 019, ACD-01 to 15. Security table empty. |
| **NFR doc** | `Requirements/requirements_specifications.docx` | 8 Oct | UC-001 to 012, class model, sequences, CF-01 to 06, data requirements, NFR-001 to 019, SEC-001 to 005. Adds the finance specialisation. |
| **Architecture** | `Architecture/high_level_architecture.docx` | 25 Oct | Components, ADR-001 to 006, costs, risks. |
| **Prototype scope** | `Requirements/prototype_requirements.docx` | 29 Oct | Phase 1 rows 1–9, Phase 2 rows 1–10. |

I took "NFR" to mean the requirements specification, because it is the document that
carries the NFR and security tables and the newer finance scope. Where it and the FR doc
differ, it wins, as you asked. If you meant something else by "NFR", sections A1 and A2
are the ones to re-read.

The larger problem is not FR against NFR. It is that the **architecture changes
requirements that neither requirements document contains**. Section A1 covers that.

---

## Part A. Alignment between the documents

### A1. Requirements that exist only in the architecture

The architecture cites these as if they were agreed requirements. None is defined in
either requirements document.

| Item | Where it appears | Problem | Suggested resolution |
|---|---|---|---|
| NFR-004 "realigned" to 95% availability | Arch. §7.1 | Both requirements documents say 99%. An architecture cannot lower a requirement. | Decide one figure. 95% is honest for one VM; change NFR-004 itself and record why. |
| NFR-020 (exact-decimal, recomputed money) | Arch. §2, §7.1 | Marked "new"; no source. The NFR doc's "Numerical validation" row is the nearest text. | Add to the NFR table. It is a good requirement. |
| NFR-021 (PKR default, Pakistani fiscal year, SBP/PBS data) | Arch. §7.1 | The NFR doc commits to no provider and no market, and UC-004 A3 says "no financial default is silently assumed". A PKR default contradicts that. The simulator's 30 jobs are all USD with US/GB clients. | NFR doc wins: no default currency. Keep PKR, fiscal year and lakh/crore as supported options confirmed per brief. State the target market in the introduction. |
| AIR-007 (finance recommendations) | Arch. §4, §7.3 | No AIR-007 exists. UC-008 and UC-012 only say "newly agreed finance extension". | Write AIR-007 in the same 11-row format as the other AIRs. |
| CON-01 (USD 80/month) | Arch. §2, §9 | No CON list exists; NFR-012 says "no fixed monthly spending ceiling is specified". | Add CON-01 to the constraints table as a project constraint and reword NFR-012 so the two do not read as a contradiction. |
| Reduced evaluation sets (60 briefs, not 120, and so on) | Arch. §9.2 B | AIR-001 to 006 still state the larger sets. ACD-14 requires agreed changes to be documented. | Update each AIR's dataset row, or keep the AIRs and call the reduced plan an interim run. |
| Freelancer.com chosen | ADR-006 | Both requirements documents still say "to be selected between Upwork and Freelancer.com" (introductions, ACD-01, data sources, `LiveMarketplaceAdapter`). | Replace with the decision and a pointer to ADR-006. |

### A2. Where the FR doc is behind the NFR doc

The NFR doc wins on each of these. The FR doc needs the edits.

1. **Finance is missing from the FR doc entirely.** No FR covers financial analysis,
   scenario models or business-planning advice (UC-008 A4/A5), financial input checks
   (UC-005 A3) or financial scope fields (UC-004 A3). AIR-005 lists data, research and
   writing only. The introduction, glossary and ACD-06 do not mention finance.
2. **UC-005 has no functional requirement.** It traces to FR-009, FR-017 to 019 and
   FR-030, none of which requires receiving client material, recording its permission
   and source, versioning the input set, or blocking unvalidated inputs. Add one FR for
   source-material intake and validation.
3. **Two actors are missing**: Reference information service and Financial
   reference-data provider.
4. **FR-004's policy fields do not match UC-001 step 6**, and the prototype uses a third
   list. See A3.
5. **The Security section is empty** and still contains a personal note ("I assumed
   that section 8 was for week 2…"). Delete the note and point to SEC-001 to 005.
6. **ACD-06 is self-contradictory**: it supports Python and React/TypeScript "along with
   other stacks" and then puts "unsupported technology stacks" out of scope.

Suggested new FR entries, numbered after FR-031 so existing references stay valid:

- **FR-032 Source materials**: receive, permission-check, version and validate client
  and reference inputs; unvalidated inputs do not feed tasks (UC-005).
- **FR-033 Financial analysis**: confirmed currency, units, periods and scenarios;
  executed calculations reconciled to source; observations, assumptions, projections and
  recommendations labelled separately (UC-008 A4/A5, NFR-020).
- **FR-034 Advice scope**: business-planning recommendations only; personal investment,
  tax and personal-finance advice declined; delivery under policy (UC-009 A1, AIR-007).

### A3. One autonomy policy, four different definitions

| Source | Fields |
|---|---|
| FR-004 | allowed actions, bid limits, daily submission limits, deadline limits, project budgets, maximum active workers |
| UC-001 step 6 | action permissions, bid and spending limits, deadlines, workload limits, deployment targets, review conditions |
| Prototype row 5 and code | allowed actions, max bid, daily proposal limit, workload limit, **daily AI spending cap**, review conditions (code adds minimum job budget, excluded keywords, minimum deadline days) |
| Architecture | all of the above, plus a platform-wide daily spending limit (default USD 4) held in the Model Gateway, a per-project provider allowlist, communication and delivery permissions |

The daily AI cap is an owner policy field in the prototype and platform configuration
in the architecture. Pick one. I suggest a single policy schema, written once in the NFR
doc and referenced everywhere, with three groups: *permissions* (which action types may
run unattended), *limits* (bid, proposals per day, workload, project budget, daily and
monthly spend, deadlines) and *review conditions*. Deployment targets and the provider
allowlist are per project and belong on the project, checked by the same Policy Service.

### A4. Conflicts that reduce autonomy

Your goal is unattended operation. FR-007 and FR-025 AC-3 say the same: within policy,
work proceeds without approval. Three places in the architecture hard-code a human step
instead:

| Hard-coded gate | Conflicts with | Suggestion |
|---|---|---|
| "All finance recommendations in the first release" need owner review (AIR-007, §4.1) | UC-009 A1: "If policy permits verified business-planning recommendations, deliver automatically." | Make it a review condition that is on by default and that the owner may switch off once AIR-007 thresholds are measured. The prototype already has a `finance_jobs` review condition. |
| Every lesson needs owner approval before use | Nothing directly, but it is a recurring manual task | Keep it for the pilot; make it a policy permission. |
| Edits to existing tests need approval | AIR-004 already forbids weakening tests | Keep. This one is a safety control, not an autonomy cost. |

### A5. Lessons Store against the retention rules

The architecture says approved lessons "outlive the 90-day project retention". The NFR
doc says derived files, indexes and summaries follow the 90-day rule, that permission
for an assignment does not authorise reuse elsewhere, and UC-011 says deleted client
material is not "retained through a new summary". A lesson is a summary derived from one
client's work and reused for others, and it keeps a pointer to its source project, so it
is not irreversibly anonymised either.

Options: (a) record the client's reuse permission before drafting lessons, and delete
lessons with the project when permission is absent; or (b) at retention expiry, drop the
source-project pointer so the lesson meets FR-030's "irreversibly anonymized" wording,
and say so in NFR-018. Either way the requirement text must change; today the two
documents disagree.

### A6. Smaller inconsistencies

- **Sequence diagrams**: only SEQ-001 to 004 and 006 to 008 exist. SEQ-005 and 009 to
  012 are missing, and the class section refers to "SEQ-001 to SEQ-009".
- **Class figures**: 5.2, 5.3, 5.5, 5.7 and 5.8 are described but not drawn. The text
  says this is deliberate; say when they will follow.
- **Architecture §4 says** the Embedder, Retrieval Index, Lessons Store and Scope Guard
  "all appear in the architecture diagram". They do not. The Evaluation Vault and Plan
  Validator are also absent.
- **The diagram draws** the Marketplace Simulator, Backup Job, Evaluation Runner and
  Secrets Store inside the Workflow Worker box. The text deploys them as separate
  containers or an external service.
- **Consent for DeepSeek and Z.ai**: the architecture needs "the client's recorded
  agreement" before confidential data goes to those providers. No use case or FR
  collects it. Add it to UC-004 or UC-005.
- **Prototype row 6** fetches "on demand"; FR-005 requires continuous discovery cycles.
  That is fair for a prototype, but see B1.
- **Use-case diagram captions**: "resolve expectations" should be "exceptions".
- **Team list** differs between the FR doc (five members) and later documents (four).

---

## Part B. Architecture: suggested improvements

Ordered by how much each affects the goal.

### B1. The design has no way to hear from the world

`MarketplaceAdapter` has `list_listings`, `submit_bid`, `get_bid_status`, `send_message`
and `submit_delivery`. There is no operation to read client messages, awards, delivery
feedback, acceptance or attachments, and no component that polls or receives them. UC-003
step 5, UC-004 and UC-009 all depend on inbound events. The class model lists
"capability discovery" on the adapter, and FR-002 needs it; the interface omits it.

Add:

- `capabilities()`, `list_events(cursor)` (messages, award, status, acceptance) and
  `get_attachment(id)` to the adapter interface and the simulator;
- an **Inbox** component in the Workflow Worker: polls on the Scheduler's cycle, stores
  the provider cursor, de-duplicates by provider event ID, and writes each event with its
  ActivityEvent in one transaction. This is also what makes FR-010 AC-2 (duplicate award
  events) and UC-005 step 1 (client files) implementable.

### B2. Independent verification is undefined for live work

Readiness rests on "hidden acceptance tests" outside the coder's reach. In evaluation
they come from the Evaluation Vault. For a real client job nobody has written them, and
the architecture does not say who does. Without that, the live gate is the coder's own
tests plus a reviewer who "can only add issues".

Add a **Test Author** role: runs on a different model family from the coder, derives
acceptance tests from the confirmed PRD requirements before coding starts, and stores
them where the coding sandbox cannot read or change them. The Plan Validator then
requires every confirmed requirement to have at least one such test.

### B3. Process boundaries and row-level security

- The Policy Service lives in the Workflow Worker, but policy saves and approvals arrive
  at the API Service. State that policy is a shared library used by both processes, and
  that the API only writes commands which the worker executes.
- "Row-level security limits each session to its project" does not hold if both services
  connect with the database owner password, because that role bypasses RLS. The Phase 1
  SQL file says exactly this: the API "connects as the postgres role (which bypasses
  RLS)". For RLS to be a real second layer, connect as a role without `BYPASSRLS` and
  set the owner or project ID per transaction.
- `LISTEN/NOTIFY` needs a session-mode connection; it does not work through a
  transaction pooler. Record that, and that NOTIFY payloads are limited to about 8 KB, so
  send the event ID and let the API read the row.
- The browser's `EventSource` cannot send an `Authorization` header. Decide now between a
  fetch-based stream and a short-lived stream ticket.

### B4. Cost controls do not add up to CON-01

- A daily limit of USD 4 allows USD 120 a month of model spend. CON-01 leaves about
  USD 50 after the VM. Add a monthly cap, or lower the daily default to about USD 1.60.
- Table A does not cost finance recommendations on `gpt-6-sol` (AIR-007); finance is
  folded into a `deepseek-v4-pro` row.
- There is no cost model for a live project whose client has not agreed to DeepSeek or
  Z.ai. Coding then runs on the expensive tier and the USD 5 bundle cap (AIR-004) is
  unlikely to hold. Cost that case, or make the agreement a precondition for pursuit.

### B5. Recovery

- An hourly `pg_dump` cannot guarantee NFR-006's one-hour loss limit: worst case is one
  hour plus the dump time. Dump every 30 minutes or state the limit as 75 minutes.
- After a restore, Outbox rows for actions sent in the lost window are gone, so the
  reconciler has nothing to check. Add a restore step that lists the account's own bids,
  messages and deliveries since the backup time and rebuilds the missing Outbox rows.
- Artifacts have a single copy in R2. Content-hash names protect against overwrite, not
  against deletion. Turn on object versioning or accept and record the risk.
- Exactly-once works for bids because the provider can be asked whether a bid exists.
  Messages have no such key. Define how a sent message is recognised (for example a
  short reference line) or accept owner handoff after a timeout.

### B6. Things an unattended freelancer needs that no document covers

- **Out-of-band alerts.** NFR-016 puts alerts in the hub within 60 seconds. An owner who
  is not watching the hub sees nothing. Add email or push for held actions and failures.
- **Money in.** The lifecycle ends at client acceptance. Add read-only tracking of
  milestone and payment status, and net marketplace fees out of the expected-return
  figure used in ranking (FR-006).
- **Marketplace limits.** Check Freelancer.com's bid allowance for your membership level
  and its rules on automated bidding and on messaging before a bid. If pre-bid messages
  are not allowed, the "clarify" class needs another path, such as questions inside the
  proposal. Model the bid allowance as a policy limit next to the daily proposal limit.
- **Memory on the VM.** API, worker, simulator, embedding model, backup job and
  evaluation runner share 4 GB. Measure it in Sprint 1; a hosted embedding call or an
  ONNX build of the model is the fallback.

### B7. Sequencing risk

Phases 1 and 2 of the prototype stop at project activation. Nothing that plans, writes
code in a sandbox or verifies it is built until after the prototype, and those parts
carry the hardest targets (AIR-003, AIR-004) and risks 14 and 15. I recommend a thin
spike during Phase 2: one task, one sandbox, one acceptance test, one pass through the
gate. It will tell you early whether the USD 5 cap and the 70% target are realistic.

---

## Part C. Phase 1 code review

Baseline: 91 API tests pass; the hub passes ESLint and `next build`.

### C1. What is sound

- Owner isolation is consistent: every query filters on `owner_id`, another owner's job
  returns the same 404 as a missing one, and tests cover it.
- The AI only estimates. `rules.py` decides pursue, clarify or decline, and stale
  assessments can never be eligible. This matches SEC-003 and AIR-001.
- Assessments are versioned against listing, profile and policy, and a policy-only
  change reuses the AI output at no cost (UC-002 A1).
- Client name, country and rating are never sent to the model (AIR-001 fairness).
- Failed and invalid model calls are still written to the cost ledger.
- Tests are named by prototype row and drive the simulator over real HTTP.

### C2. Defects found and fixed

Each was reproduced against the original `phase1/` code before fixing, and has a test in
`phase1/api/tests/test_review_fixes.py`.

| # | Defect in the original code | Effect | Fix |
|---|---|---|---|
| 1 | A listing that disappears from the marketplace stays in the feed as pursue-eligible (`services/feed.py`, `services/discovery.py`). | In Phase 2 the system would bid on closed jobs (UC-003 E1). | Listings not returned by the last successful fetch are marked `is_closed`, lose eligibility and sink to the bottom. A failed fetch closes nothing. |
| 2 | A stored listing that the policy filters later exclude is skipped on fetch and never refreshed (`discovery.py`). | It shows outdated content indefinitely. | Filters now stop only new listings; known ones are refreshed and then declined by the rules. |
| 3 | The feed sorts by score alone, so declined jobs rank above clarify jobs (seen: decline 51.0 above clarify 50.0). | The "ranked list" is not a pursuit ranking (FR-006). | Order is pursue, clarify, decline, then score. |
| 4 | The daily cap is checked as `spent >= cap` before a call (`services/common.py`). | Spend passes the cap by one call; with a real model that is an unbounded amount (NFR-011). | The call's reservation is counted before it starts: `spent + reserve > cap` refuses the call. |
| 5 | If LiteLLM has no price for the model, cost is recorded as 0 (`llm.py`). | An unpriced model never reaches the cap (FR-026 AC-2). | Unknown prices are costed at a configurable fallback rate. A `max_tokens` ceiling is also set. |
| 6 | Editing the profile leaves the pending AI draft in place (`routers/profile.py`). | Its citations (E1, E2…) point at the wrong evidence after a reorder; accepting it breaks FR-003 AC-1. | Any real profile change discards the pending draft. |
| 7 | Each "Assess" press while capped adds one `unassessed` row per job (`services/assessment.py`). | History and table grow without limit. | A repeat of the same failure against the same versions refreshes the existing row. |
| 8 | `latest_by_listing` loads every assessment row the owner has ever had. | Feed latency grows with history (NFR-001). | The newest row per listing is selected in SQL. |
| 9 | Two policy saves at once collide on the unique version and return HTTP 500 (`routers/policy.py`). | Unhandled error. | Returns 409 with a clear message. |
| 10 | `/sim/chaos/*` is mounted in the deployed API with no authentication. | Anyone can break fetches or add listings for every owner. | Optional `SIMULATOR_CHAOS_TOKEN`; when set, chaos calls need it in `X-Sim-Token`. |
| 11 | Listing text reaches the model with no injection handling, and the model's `fit` decides eligibility. | A listing saying "rate this a perfect fit" can become pursue-eligible (SEC-003). | The prompt marks the listing as untrusted, and a deterministic check holds any listing with instruction-like text for review. All 30 simulator listings pass it. |
| 12 | The jobs table opens the drawer by row click only; the drawer has no dialog role or Escape key. | Not operable by keyboard (NFR-010, WCAG 2.1.1). | The title is a real button; the drawer is `role="dialog"`, takes focus and closes on Escape. |
| 13 | MFA is never checked, although SEC-001 and the architecture require it. | Password-only sessions are accepted. | `REQUIRE_MFA=true` rejects sessions that are not `aal2`. Off by default so existing accounts keep working. |

Two existing tests changed because the behaviour changed on purpose: the cap test now
expects 2 calls rather than 3 (defect 4), and the feed-order test checks decision tier
and then score (defect 3).

### C3. Gaps against the architecture, not fixed

These are design work for Phase 2 rather than bugs.

1. **Everything runs inside one HTTP request.** `POST /jobs/fetch` fetches and then
   assesses every job in turn. With a real model that is up to 27 calls of up to 60
   seconds each, with one retry. Hosting platforms will cut the request long before it
   finishes. Phase 2 needs the Workflow Worker and a Postgres task queue from ADR-005,
   and this is the first thing I would build.
2. **No ActivityEvent or Outbox tables.** Phase 2 rows 4, 5 and 10 need both. Add them
   before the first proposal is submitted, not after.
3. **No Policy Service.** Ranking and policy gating are mixed in `rules.classify`. Phase 2
   needs `policy.check(action)` returning allow or hold together with a hash of the exact
   payload, so that approvals can bind to it (FR-029, SEC-003).
4. **No schema migrations.** `create_all` never alters a table. Commit `4e42216` added
   columns to existing tables, so any database created before it now fails. Use Alembic.
5. **Money is stored as `Float`.** Bids are money; NFR-020 requires exact decimals. Use
   `Numeric` and send amounts as strings.
6. **The adapter is not yet an interface.** `SimulatorAdapter` is the type used
   everywhere, `simulated=True` is hard-coded in `discovery.py` rather than taken from
   the adapter's capabilities, and `get_connection` hard-codes the provider. Define a
   `MarketplaceAdapter` protocol now so the Freelancer.com adapter drops in (NFR-013).
7. **The model gateway is a single model.** There is no role routing, fallback model,
   redaction or prompt versioning. Assessments do not record the model or prompt version,
   so changing either does not make old assessments stale, although the architecture's
   cache key includes both.
8. **Scoring.** The "price" part rewards a higher price regardless of effort, and the
   hourly rate that is already computed is not used. Workload is only checked for zero.
   Prices are compared with `max_bid` without regard to currency.
9. **No rate limiting** on any endpoint (SEC-005), and no issuer check on the JWT.
10. **Project hygiene.** The README was removed in the latest commit, but `config.py`
    still points to it and the Phase 1 submission needs `Readme-Prototype.txt` and the
    code review checklist. There is no CI workflow, Dockerfile or Compose file, and no
    hub tests.

---

## Part D. What changed in `phase1/`

The prototype runs with the same commands and environment variables as before. Changed
files, relative to `Prototype/phase1/`:

- API: `app/auth.py`, `app/config.py`, `app/llm.py`, `app/rules.py`,
  `app/routers/policy.py`, `app/routers/profile.py`, `app/services/assessment.py`,
  `app/services/common.py`, `app/services/discovery.py`, `app/services/feed.py`,
  `simulator/app.py`, `.env.example`
- Tests: new `tests/test_review_fixes.py`; two expectations updated in
  `tests/test_row7_assessment.py` and `tests/test_row9_feed.py`
- Hub: `src/app/(hub)/page.tsx`, `src/components/Badges.tsx`,
  `src/components/JobDrawer.tsx`, `src/lib/types.ts`

No database columns were added, so the code runs against an existing Phase 1 database.

Verification: `pytest` in `api/` gives 105 passed; in `hub/`, `eslint`,
`tsc --noEmit` and `next build` are clean. The basic flows and every fix that has a
visible effect were then checked in headless Chromium against a local deployment (SQLite,
mock model). Sign-in was checked against a local stand-in for Supabase Auth, so real
Supabase sign-in and MFA enrolment remain untested, as does any real model or deployed
host. Fixes 5 and 8 have no visible effect and rest on unit tests only.

That browser pass found four more problems, fixed afterwards and re-checked the same way:

- **Sign-in after sign-out.** The login page stays mounted behind the hub and kept its
  "Signing in…" state, so a second sign-in needed a page reload (`login/page.tsx`).
- **Small AI caps.** A cap of 0.0025 was shown as "$0.00" in the unassessed reason and the
  policy history, which read as spend over the cap (`assessment.py`, `policy/page.tsx`,
  `lib/format.ts`).
- **Decision badge.** Closed jobs and jobs held for review still showed a green "pursue".
  Closed ones are now struck through and held ones read "pursue · needs review"
  (`Badges.tsx`).
- **Drawer focus.** Tab could leave the open drawer and Escape dropped focus on the page
  body. Tab now stays inside and focus returns to the job title (`JobDrawer.tsx`).

New settings (all optional): `LLM_CALL_RESERVE_USD`, `LLM_MAX_OUTPUT_TOKENS`,
`LLM_FALLBACK_USD_PER_1K_TOKENS`, `REQUIRE_MFA`, `SIMULATOR_CHAOS_TOKEN`.

## Suggested order of work

1. Decide the items in A1, A4 and A5 and issue one updated requirements baseline that
   includes FR-032 to 034, AIR-007, NFR-020, NFR-021 and CON-01.
2. Write the single policy schema (A3) before building Phase 2 row 2.
3. Add the inbound-events operations to the adapter and simulator (B1). Phase 2 rows 5
   and 6 cannot be built without them.
4. Start Phase 2 with the worker, task queue, ActivityEvent, Outbox and migrations (C3
   items 1, 2 and 4), then build the proposal rows on top.
5. Run the build-and-verify spike (B7) in parallel.

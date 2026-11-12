Project: Autolancer (P07)
Team:    Huzayfah Abid    (27100271)
         Zainab Raza      (27100435)
         Muhammad Hashim  (27100437)
         Muhammad Zakaria (27100222)

Submission: Prototype Phase 1


PROTOTYPE SUBMISSION GUIDELINES

1. Properly tested working system deployed on an online hosting platform.
2. Code with readable comments uploaded in “Prototype” folder of your project’s Github repository.
3. For prototype phase-2 only: 3-4 minutes video that explains the functionality of the prototype. This must be uploaded in “Prototype” folder of your project’s Github repository.
4. This "Readme" file must be uploaded in the "Prototype" folder.



------------------------------------------------------------------------------------------------

LIST OF REQUIREMENTS COMPLETED IN THE PROTOTYPE


PHASE 1 - COMPLETED. 

 #  Use case                                                        Developed by
--- --------------------------------------------------------------- ------------------------
 1  Owner sign-in and sign-out. Access is limited to the owner's    Huzayfah Abid     
    own data; a failed sign-in reveals no account or project data.
    (UC-001 step 1, E1; FR-001)

 2  Connect the Marketplace Simulator and show its connection       Huzayfah Abid     
    status and supported operations. An unneeded integration stays
    disconnected; a failed connection is marked unavailable.
    (UC-001 steps 2-3, A1, E2; FR-002)

 3  Set up the owner profile: offered services, a short skills      Huzayfah Abid     
    summary and evidence of past work.
    (UC-001 step 4; FR-003)

 4  AI drafts a profile from the services and evidence and flags    Huzayfah Abid     
    claims without evidence. The owner can accept the draft or
    ignore it and keep their own profile.
    (UC-001 step 5, A2, E3; FR-003; AIR-002)

 5  Set autonomy limits: allowed actions, maximum bid, daily        Huzayfah Abid     
    proposal limit, workload limit, daily AI spending cap and
    review conditions. Each valid save becomes a new policy
    version; invalid values are rejected and nothing is saved.
    (UC-001 steps 6-7, E3; FR-004)

 6  Fetch jobs from the Marketplace Simulator on demand, apply the  Huzayfah Abid     
    job filters and store them without duplicates. If a fetch
    fails, the last list is kept and the time it was last updated
    is shown.
    (UC-002 steps 1-2, E1; FR-005)

 7  AI assessment of each new job (category, fit, effort and price  Huzayfah Abid     
    estimate, open questions) within the daily AI cap. Failed or
    over-cap assessments are marked unassessed and can be retried.
    (UC-002 steps 3-4, E2; FR-006; AIR-001)

 8  Classify jobs as pursue, clarify or decline and rank them. A    Huzayfah Abid     
    changed profile, policy or job listing triggers re-assessment
    of the affected jobs.
    (UC-002 steps 5-6, A1, A2, E3; FR-006)

 9  View the ranked job feed with filters, new and changed          Huzayfah Abid     
    markers, the AI's reasons, and jobs flagged as eligible for
    pursuit.
    (UC-002 step 7; FR-006, FR-025)


PHASE 1 - OTHER WORK COMPLETED

    Work                                                            Done by
--- --------------------------------------------------------------- ------------------------
 *  DEPLOYMENT. The whole prototype put online and working: the     ZAINAB RAZA
    Supabase database and sign-in, the API on Render, the Owner
    Hub on Vercel, and the three connected and tested together.
    (Submission guideline 1)

 *  GITHUB PROJECT MANAGEMENT. Planning, organising and tracking    MUHAMMAD HASHIM
    the team's work for this phase in the GitHub project.


PHASE 2 - Listed for completeness.

 1  AI drafts a tailored proposal for a pursue-eligible job (UC-003 steps 1-2)
 2  Check the exact proposal against the active policy; hold it for owner
    review when required (UC-003 step 3)
 3  Owner approves, rejects or revises a held proposal; the decision is
    recorded (UC-003 A1, UC-010 steps 2-4)
 4  Submit an approved proposal to the Marketplace Simulator once and record
    its receipt (UC-003 step 4)
 5  Receive proposal status updates, the simulated award and client messages
    (UC-003 step 5)
 6  Per-project client conversation with AI-extracted requirements and
    clarification questions (UC-004 steps 1-6)
 7  Create and version the project brief or PRD, and release it once confirmed
    (UC-004 steps 7-8)
 8  Activate one project only after the award and a confirmed brief exist,
    without duplicates (UC-003 steps 6-7, E3)
 9  Pause, resume and stop a project from the Owner Hub (UC-010 steps 3-5)
10  Project activity log in the Owner Hub (FR-025, NFR-015)



------------------------------------------------------------------------------------------------

HOW TO ACCESS THE PROTOTYPE


Open the Hub in a web browser and sign in with the accounts provided below. Sign-up is not part of the phase 1 use cases. Nothing needs to be installed.

    Owner Hub:   https://autolancer-hub.vercel.app
    API (if you want to test this too):    https://autolancer-api-1.onrender.com

    >>> Deployed and hosted by ZAINAB RAZA. <<<

Two accounts are provided. There is no sign-up page; owner accounts are
created by the team.

    Account 1 - already set up, with jobs fetched and ranked
        Email:     zainabrz778@gmail.com
        Password:  G-L,d;F.dDr5SX+

    Account 2 - empty, to walk through setup from the start
        Email:     mishalraza8146@gmail.com
        Password:  G-L,d;F.dDr5SX+

Please note before you start:

  * The first page after a quiet period can take up to a minute to load. The
    API is on a free hosting plan that sleeps when idle.

  * A new account must complete three pages, in this order, before
    "Fetch jobs" will work:
        1. Connections - tick "Enabled" to connect the Marketplace Simulator.
        2. Profile     - choose services, add a skills summary and evidence.
        3. Policy      - save an autonomy policy.




------------------------------------------------------------------------------------------------


ADDITIONAL INFORMATION


================================================================================================
  WHO DID WHAT

  HUZAYFAH ABID      CODE
                     Developed the code for all nine Phase 1 use cases.

  ZAINAB RAZA        FULL DEPLOYMENT
                     Set up the Supabase database and sign-in, deployed the API on Render
                     and the Owner Hub on Vercel, connected the three and got the whole
                     prototype working online. Without this there is no hosted system to
                     grade (submission guideline 1).

  MUHAMMAD HASHIM    GITHUB PROJECT MANAGEMENT
                     Planned, organised and tracked the team's work for this phase in the
                     GitHub project.
================================================================================================


Frontend Design

  Please pardon the ugliness, its design was not something we felt
  important at the prototype stage and hence we gave Claude the reins.
  It is not very tasteful.


Hosting

  Owner Hub on Vercel, API on Render, sign-in and Postgres database on
  Supabase. Region: Singapore. Deployed by Zainab Raza.

The AI model

      The deployed prototype runs with the model gateway in "mock" mode. In
      this mode no external AI model is called: assessments and profile
      drafts are produced by a deterministic stand-in so the prototype can be
      used without cost. Everything around the model is real and can be
      exercised: the spending cap, the cost ledger, output validation, the
      rules, ranking, versioning and re-assessment. A real model is selected
      by changing one setting (LLM_MODEL) and adding the key.


Known limits of Phase 1

  * The marketplace is the simulator only; no live marketplace is connected.
    All listings are marked "simulated".
  * Jobs are fetched when the owner presses the button. Scheduled discovery
    cycles are not part of Phase 1.
  * Proposals and projects are Phase 2. The daily proposal limit and workload
    limit are saved and versioned now, but in Phase 1 they only affect
    whether a job is shown as eligible.
  * Fetching assesses all new jobs within one request. With a real model and
    many jobs this can be slow; unfinished jobs stay marked for assessment
    and "Assess" continues from there. A background worker is planned.
  * Two-step sign-in is supported but switched off on purpose.
  * Money values are stored as floating-point numbers for simplicity.
  


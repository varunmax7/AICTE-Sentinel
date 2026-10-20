# Decisions log

Per `IMPLEMENTATION.md` §0.2 rule 9: when a spec detail is missing, the simplest option
consistent with the spec is chosen and recorded here.

## P0 — Repo, infra, tooling

- **pnpm workspace scope**: only `apps/web` and `packages/*` are pnpm workspace members.
  `apps/api` and `apps/voice` are Python (`uv`) projects and are intentionally excluded from
  `pnpm-workspace.yaml`; Turborepo tasks for them are invoked as passthrough shell scripts
  (`turbo.json` tasks call into `uv run ...` via each app's own `package.json`-less tooling is
  not used — instead, root `package.json` scripts and CI steps call `uv` directly for the Python
  apps, while `turbo run <task>` drives the JS side).
- **Next.js version**: scaffolded with `create-next-app@latest` (App Router, TypeScript,
  Tailwind, ESLint, Turbopack, pnpm) rather than pinning an exact version string in this doc,
  since `create-next-app` always resolves the current stable Next 15.x/React 19.x pair.
- **apps/voice in P0**: per IMPLEMENTATION.md §5/§20-V0, Track V owns `apps/voice`. For P0 it is
  scaffolded as a bare FastAPI skeleton (`/health` only) so `docker compose up` and CI are green
  end-to-end; Rishanth fills in `/voice/*`, ConversationRelay, and the agent brain starting at V0.
- **DB migrations tool**: Alembic is initialized but P0 ships no domain models yet (those start
  in P1). The `alembic/versions` directory is created with a `.gitkeep` so the migration chain
  has a stable home from the start.
- **`audit_events` DB-role lockdown deferred to P12**: §16/§21 want the app's DB role restricted
  to `INSERT, SELECT` only on `audit_events` (no UPDATE/DELETE), enforced by Postgres grants. That
  requires the table to be owned by a *different*, non-connecting role than the one the app
  authenticates as (table owners always bypass GRANT/REVOKE on their own objects), which means a
  second DB role split between "runs migrations" and "runs the app" — infra not worth building
  before there's a deployment story. Until Phase P12 (Hardening) does that properly, `audit_events`
  is protected at the application layer only: every write goes through
  `app.services.audit.chain.write_audit_event`, which only ever INSERTs, and no router/service
  calls UPDATE or DELETE against the table. `app.services.audit.chain.verify_chain` (added in P1,
  covered by `tests/test_audit_chain.py`) recomputes the hash chain and is what actually detects
  tampering if that application-layer discipline is ever bypassed (e.g. a manual DB edit) — the
  `GET /audit/verify` endpoint that exposes it to the admin audit explorer is P10 scope.
- **Secrets**: `.env.example` is committed verbatim from §6; a local `.env` (gitignored) must be
  created by each developer (`cp .env.example .env`) before `docker compose up`.
- **Linting**: `ruff` + `mypy` for both Python apps (shared `pyproject.toml` tool config per app,
  not a shared root config, since `apps/api` and `apps/voice` have independent dependency sets).

## P1 — Auth, RBAC, design system, theming, i18n shell

- **Local Postgres/Redis for dev and tests, not Docker**: this environment's network can't reach
  Docker Hub at all (TLS handshake timeouts — see the P0 chat record), so `docker compose up`
  can't be exercised here. Homebrew already had Postgres 17 and Redis running locally on this
  machine for another project; rather than block all backend work on that network issue, local
  Postgres/Redis (`createuser/createdb acp`, default `DATABASE_URL`/`REDIS_URL` already point at
  `localhost`) are used for migrations, the seed script, and the full pytest suite. The Docker
  Compose stack (`infra/docker-compose.yml`) is unchanged and is the real target for anyone with
  normal network access; this is purely how *this session* validated P1 without it.
- **Login identifier is always a phone number against `users.phone_hash`**: §13.1 doesn't say
  whether institution logins go through `users` or `institution_contacts`. `institution_contacts`
  is explicitly a notification-targeting table (multiple contacts per institution, used by the
  notification orchestrator from P7), not a login table, so every role that can call
  `/auth/otp/*` — `INSTITUTION`, `SCRUTINY_OFFICER`, `REGIONAL_OFFICER`, `BUREAU_HEAD`,
  `COMMITTEE_MEMBER`, `EVC_EXPERT`, `ADMIN` — logs in as a `users` row matched by `phone_hash`.
  `PUBLIC` has no login at all and `FACULTY` uses its own `/faculty/otp/*` endpoints (§13.12)
  against the (future) `faculty` table, not `users` — both are rejected by `/auth/otp/*` with
  `ROLE_NOT_LOGINABLE`.
- **`user_settings` as its own table**: the P1 task list names a `user_settings` table, but §21's
  schema folds `preferred_language`/`theme`/`voice_pin_hash` straight into `users` and never shows
  a separate settings table. Notification-channel preferences and call opt-in/time (mentioned for
  `/me` in §13.1 prose) don't have an obvious home in §21 either. Resolved by keeping the §21
  fields on `users` directly, and adding a small separate `user_settings` table
  (`email/whatsapp/sms/call_opt_in`, `preferred_call_time`) for the channel-preference bag the
  task list anticipated — it'll get real columns to toggle once P7's notification orchestrator
  exists to read them.
- **SSE broadcasts globally, not per-recipient, in P1**: `/stream` subscribes every connected
  client to one Redis channel (`acp.events`) and relays every published outbox event verbatim.
  Real per-recipient targeting needs the notification orchestrator's recipient resolution (§11.1),
  which is P7. The frontend's `NotificationCenter` already treats an SSE message as "something
  happened, not necessarily for you specifically" rather than rendering it as a personal
  notification, so narrowing this later (e.g. filtering on a `recipient_user_id` field) won't
  require a client-side redesign.
- **Outbox publish is nudge + beat safety net, not strictly transactional delivery**: after a
  commit that wrote an `outbox_events` row, the API fires `celery_app.send_task(...)` to publish
  it to Redis pub/sub immediately; if the broker call itself fails, that's logged and swallowed
  rather than failing the request, because Celery Beat's `publish_pending` task (every 5s) will
  pick up anything unpublished regardless. This keeps event delivery best-effort/eventually
  consistent rather than coupling the user-facing request to broker availability.
- **Twilio Verify adapter is real but untested against live Twilio in this session**: no Twilio
  credentials are configured here, so `OtpProvider` is only exercised through its `DEMO_MODE`
  branch (accepts `DEMO_FIXED_OTP`, never calls Twilio). The non-demo code path (`twilio.rest`
  Verify `verifications.create` / `verification_checks.create`, wrapped in `asyncio.to_thread`
  since the SDK is sync-only) is written to the documented Verify v2 API but not live-tested;
  flag this when Twilio credentials are actually available.
- **`audit_events` DB-role lockdown deferred to P12**: see the P0 section above — now that
  `write_audit_event`/`verify_chain` exist and are tested, the remaining gap is purely the
  Postgres-grants enforcement, intentionally left for the hardening phase.

## P2 — Workflow engine + application lifecycle

- **Branch condition syntax deviates from §9.2's illustrative example**: that example writes
  `application.payload.is_government == true && stage == 'SAC'`, but `&&`/`true` (lowercase) are
  JavaScript, not valid Python — and `simpleeval` (the evaluator §9.2 names) parses a Python-like
  grammar. `app.services.workflow.conditions.evaluate_branch_condition` uses `and`/`or`/`True`
  instead; the seed `NEW_INSTITUTION` rule's one branch (`skip: false`, so functionally inert)
  uses the corrected syntax and round-trips through the real validator + evaluator, proving the
  schema/engine support for branches end to end even though no seeded pathway needs a *skipping*
  branch yet.
- **Action-level OTP (submit, and future committee-decision/compliance-verify) reuses
  `otp_audit` with `OtpPurpose.ESIGN`** (already in the P1 enum, unused until now — see that
  phase's section above) rather than a new table: `app.services.auth.action_otp` mirrors the
  login flow's send/verify shape but is keyed off the *authenticated actor's own* `phone_hash` +
  `role`, not a request-supplied identifier. `POST /applications/{id}/submit/otp` sends it,
  `POST /applications/{id}/submit` verifies it inline — no separate "send" step is implied by
  §13.2's table, but requiring one before `submit` is the simplest way to give OTP confirmation a
  real send/verify round trip instead of silently trusting an unsent code.
- **`GET /applications/{id}/stages` and `GET /institutions/{id}` are endpoints not named in
  §13.2's table but added anyway**: the application-detail screen's horizontal stage stepper
  needs the ordered list of stage instances for one application (no endpoint in §13.2/§13.3
  returns that directly — `/queue` is officer-scoped and `/stages/{id}` is single-stage), and the
  8-step wizard's "Institution" step needs the institution's own name/address, which §13.2 does
  list (`GET /institutions/{id}`) but no earlier phase had implemented yet. Both are thin,
  consistently-scoped reads reusing the same region/institution scoping helpers as everything
  else.
- **`assignments.assigned_by` is a nullable FK to `users`, not the `SYSTEM|user_id` union §21
  describes**: a real union column needs either two columns or a sentinel value, both messier
  than "NULL means the workload balancer assigned it, a user id means a human reassigned it" —
  the same information, typed.
- **Deficiency respond flow lives inside the application-detail Deficiencies tab, not a separate
  `/applications/[id]/respond` route** (§15.2 lists both a tab and a route): one `resubmit()` call
  already reactivates the whole returned stage from *all* its open deficiencies' responses at
  once, so a dedicated per-deficiency route would have to collect the same batch anyway — the tab
  holding one response textarea per open deficiency plus a single "submit response" button is the
  same user flow with one less page.
- **Dashboards stay the Phase P1 `RoleHome` placeholder**: the Phase P2 task list says "dashboard
  (basic)" for both institution and officer, and `RoleHome` (name + role + "coming soon") already
  satisfies "basic" — real KPI-card dashboards per §15.2/§15.3 are a bigger, separate lift better
  left to whichever later phase actually needs them populated with real metrics (compliance
  counts, ageing, etc. mostly don't exist as data yet).
- **`DataTable` stays the plain P1 `<table>`, not TanStack Table**, for the officer queue too:
  that component's own comment flagged TanStack as landing "in Phase P2 (queue)," but nothing in
  this phase's acceptance criteria needs sorting/column-filtering — just "queue table with
  SlaBadge," which the plain table already does. Deferred again, now explicitly to whichever
  phase first needs real column sorting.
- **`app_no` generation (`APP-YYYY-NNNN`) counts existing rows in the same transaction** rather
  than a dedicated per-year sequence table — simplest option, with a known race condition under
  concurrent submits that §21 doesn't call out a sequence for either. Fine at this project's
  demo-scale concurrency; a real per-year `SERIAL`/advisory-lock sequence is a one-function change
  if it's ever needed.
- **`DECISION_RECORDED` is set the moment the rule's last stage completes**, for every pathway —
  not gated on an actual committee `DECIDE` action, which doesn't exist until Phase P5. This
  matches §9.3's state diagram (`IN_PROCESS → DECISION_RECORDED → {APPROVED|...}`) for the
  "Only Scrutiny"/"Only EVC" pathways, where there's no committee stage at all and the last human
  stage's own clearance *is* the terminal decision signal; for SAC-gated pathways,
  `DECISION_RECORDED` firing before Phase P5's real `DECIDE` action exists is an intentional
  half-step (the stage list is simply exhausted) that P5 will refine once committee decisions are
  real.
- **`REFER_SENIOR`/`REQUEST_CLARIFICATION` are audit-only transitions in P2**: §9.3's state
  diagram shows `REFERRED` as a transient state that returns straight to `ACTIVE`, so
  `perform_action` logs the transition + audit event and leaves `StageInstance.status` at
  `ACTIVE` rather than round-tripping through a `REFERRED` row — same for `REQUEST_CLARIFICATION`,
  which pauses the deadline (per `pause_clock_on`) but has no distinct named state in §9.3 either.
  Routing a referral to a specific senior officer, and resuming a clarification request on reply,
  are both left for whichever phase actually builds officer-to-officer referral UI.
- **Found and fixed while round-tripping the P2 migration**: dropping a table whose column used
  `sa.Enum(...)` does not drop the Postgres enum TYPE that created — `downgrade()` needs an
  explicit `sa.Enum(name=...).drop(bind, checkfirst=True)` per enum, or a later `upgrade` hits
  `type "..." already exists`. The *original* P0/P1 migration (`4b224e6e75ca`) had the same latent
  bug (never exercised until this phase's downgrade/upgrade testing); both migrations now drop
  their enum types on downgrade.
- **Discovered while manually exercising the new screens**: `GET /applications` crashed
  (`MissingGreenlet`) because it never loaded the `courses` relationship before serializing it —
  every other endpoint that returns an `ApplicationOut` does an explicit `db.refresh(...,
  attribute_names=["courses"])` first; the list endpoint is the one place that iterates a whole
  result set, so it needed `selectinload` instead. Fixed, with a regression test
  (`test_list_applications_includes_courses`) — a reminder that lazy-loaded relationships under
  async SQLAlchemy fail loudly only when actually awaited, so pathway tests that never touch
  `.courses` won't catch this; this is why manual exercising of a new screen against the real
  dev stack (not just pytest) is worth doing before calling a phase done.

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

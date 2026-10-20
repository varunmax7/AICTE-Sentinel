# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Entries are grouped by
implementation phase (see `IMPLEMENTATION.md` §19/§20).

## [Unreleased]

### Phase P0 — Repo, infra, tooling
- Scaffolded pnpm + Turborepo monorepo (`apps/web`, `apps/api`, `apps/voice`, `packages/contracts`).
- Added Docker Compose stack: postgres (pgvector), redis, minio, api, worker, beat, voice, web, caddy.
- Added `infra/postgres/init.sql` (vector + pgcrypto extensions, audit-only DB role).
- Added `.env.example` covering general/security/data/AI/Twilio/voice config.
- Wired lint/typecheck/test scripts (`turbo run lint typecheck test`) for web (eslint/tsc/vitest) and
  api/voice (ruff/mypy/pytest).
- Added CI workflow: install, lint, typecheck, unit tests, OpenAPI export, TS client generation.
- Added `pnpm tunnel` script (cloudflared) for exposing api + voice to Twilio webhooks locally.
- Added `docs/DECISIONS.md`, `docs/CHANGELOG.md`, `docs/DEMO_SCRIPT.md`.

### Phase P1 — Auth, RBAC, design system, theming, i18n shell
- **Backend**: `regions`, `states`, `institutions`, `institution_contacts`, `users`, `user_regions`,
  `user_settings`, `otp_audit`, `audit_events`, `outbox_events` SQLAlchemy models + Alembic env
  (async, autogenerate-ready).
- OTP login (`/auth/otp/send`, `/auth/otp/verify`, `/auth/refresh`, `/auth/logout`) via a Twilio
  Verify adapter with a `DEMO_MODE` fixed-OTP bypass; JWT httpOnly cookies; `GET/PATCH /me`.
- `require(role)` / `user_region_ids` RBAC + region-scope dependencies (`app.core.deps`).
- Hash-chained audit trail (`app.services.audit.chain`): `write_audit_event` (transactional) +
  `verify_chain` (tamper detection), with every login writing an event.
- Demo clock (`app.core.clock`, `GET /clock`) with Redis-backed time-travel offset.
- Transactional outbox → Celery → Redis pub/sub → `GET /stream` (SSE), so the notification bell
  receives live events (e.g. `auth.login`) in real time.
- `app/seed/seed.py` (`pnpm seed`): one region/state/institution + one demo user per loginable
  role, fixed OTP `123456`.
- 16 new pytest cases (auth flow, audit chain integrity + tamper detection, clock offset, field
  encryption/hashing) — see `docs/DECISIONS.md` for how they run against local Postgres/Redis.
- **Frontend**: `styles/tokens.css` (§7.2 design tokens, light/dark/system via next-themes),
  Tailwind v4 `@theme inline` mapping, Inter/JetBrains Mono/Noto Sans-per-locale fonts.
- next-intl i18n shell: `[locale]` routing, `messages/{en,hi,te,ml,ta,kn}.json` (6 full locales,
  `pnpm i18n:check` passing), language switcher.
- Shell components: `TopBar`, `Sidebar` (role-based, collapsible), `Breadcrumbs`, `ActionBar`,
  `NotificationCenter` (SSE-backed drawer), `ProfileMenu`, `ProfileSettings`.
- Core components: `StatusChip`, `SlaBadge`, `SlaPill`, `ConfidenceRing`, `AiBadge`, `IconBadge`,
  `Timeline`, `AuditDrawer`, `FileDropzone`, `DataTable`, `KpiCard`.
- OTP login page (role tabs, send/verify) wired to the real API; role-based route guards in
  `middleware.ts` (redirect unauthenticated → login, cross-role → own home, authenticated →
  role home); one dashboard + settings page per role (`institution`, `officer`, `regional`,
  `bureau`, `committee`, `admin`) plus a minimal dark-mode EVC expert placeholder.
- `/dev/components` gallery (dev-only): every component rendered in light + dark side by side.
- 5 Vitest unit tests (SLA state logic, `StatusChip` i18n rendering).

### Phase P2 — Workflow engine + application lifecycle
- **Backend**: `application_types`, `workflow_rules`, `applications`, `application_courses`,
  `stage_instances`, `stage_transitions`, `assignments`, `deficiency_reasons`, `deficiencies`,
  `deficiency_letters`, `deadlines`, `holidays` SQLAlchemy models + Alembic migration (also fixes
  a latent enum-type-not-dropped-on-downgrade bug in the P1 migration, found while round-tripping
  this one).
- Rule JSON schema (`packages/contracts/workflow-rule.schema.json`) + a Pydantic validator
  (`app.services.workflow.rules`) that parses/validates `workflow_rules.definition`.
- Workflow engine (`app.services.workflow.engine`): `route` (creates every stage instance up
  front, evaluating branch skips once against the submitted payload), `perform_action`
  (CLEAR/COMPLETE, RETURN, REFER_SENIOR, REQUEST_CLARIFICATION — role/region/assignment checked,
  one audit + outbox event per transition), `advance` (auto-advance on clear), `resubmit`
  (reactivates a returned stage, marks responded deficiencies, resumes the deadline). A tiny safe
  expression evaluator (`simpleeval`-backed) for rule branch conditions.
- Working-day calculator + holiday calendar (`app.services.workflow.calendar`); generic deadline
  create/pause/resume/close (`app.services.workflow.deadlines`); workload-balanced auto-assignment
  with manual reassignment (`app.services.workflow.assignment`); deterministic deficiency-letter
  template stub standing in for the real AI draft that lands with Document AI.
- Action-level OTP (`app.services.auth.action_otp`) reusing `otp_audit`'s `ESIGN` purpose, so
  `POST /applications/{id}/submit` is OTP-gated like the spec requires.
- Endpoints: `GET /application-types`, `GET/POST /applications`, `GET/PATCH /applications/{id}`,
  `GET /applications/{id}/stages`, `POST .../precheck` (P3 stub), `POST .../submit/otp` +
  `POST .../submit`, `POST .../withdraw`, `POST .../resubmit`, `GET .../timeline`,
  `GET .../communications` (P7 stub); `GET /queue`, `GET/POST /stages/{id}`,
  `POST /stages/{id}/actions`, the deficiency-letter draft/edit/send trio,
  `POST /assignments/{id}/reassign`; `GET /institutions/{id}`.
- Seed: all 7 Phase P2 application types + published v1 rules covering all 5 PS pathways,
  deficiency reasons, a few national holidays, and 3 demo applications (1 draft, 1 routed to
  SCRUTINY, 1 auto-advanced to EVC) exercised through the real engine at seed time.
- 17 new pytest cases: every PS pathway routes correctly, CLEAR auto-advances, RETURN pauses the
  deadline and drafts a letter, resubmit resumes and re-scrutinizes, the max-returns warning is
  recorded without blocking, role/region/assignment permission checks reject correctly, the
  workload balancer distributes across officers, and a full HTTP submit→queue→clear→timeline
  round trip.
- **Frontend**: institution `/applications` list, the 8-step `/applications/new` wizard (type →
  institution → courses & intake → land & building → faculty-import placeholder → document
  checklist → AI-precheck placeholder → OTP-gated review & submit), `/applications/[id]` detail
  (horizontal `StageStepper` + Overview/Documents/Deficiencies/EVC/Timeline/Communications tabs,
  deficiency respond-and-resubmit, withdraw, `Timeline`/`AuditDrawer` wired to the real timeline
  endpoint); officer `/queue` (table with `SlaBadge`) and `/queue/[stageId]` (stage detail with
  Clear/Return/Refer/Clarify actions and a Return modal with an AI-drafted, editable deficiency
  letter).
- New i18n keys (`applicationType`, `applications`, `deficiency`, `queue`, `stageDetail`) in all
  6 locales, `pnpm i18n:check` passing.

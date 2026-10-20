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

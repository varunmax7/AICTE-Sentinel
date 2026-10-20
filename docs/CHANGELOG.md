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

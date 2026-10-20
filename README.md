# AICTE Sentinel — Approval & Compliance Portal (ACP)

> SIH 2026 · PS 26262 · AICTE Regulation Bureau · Theme: Smart Automation

A single, secure, configurable web platform (plus an installable PWA for field inspectors) that
automates AICTE approval workflows end to end and continuously monitors undertakings and document
validity, with multi-channel alerts and a tamper-evident audit trail.

**The full product spec and phase-by-phase build plan live in [`IMPLEMENTATION.md`](./IMPLEMENTATION.md)
— read it first.** This README only covers getting the repo running locally.

## Status

Phase **P0 — Repo, infra, tooling** and **P1 — Auth, RBAC, design system, theming, i18n shell**
(see `IMPLEMENTATION.md` §19) are complete:

- Monorepo scaffolded: `apps/web` (Next.js), `apps/api` (FastAPI), `apps/voice` (FastAPI
  skeleton), `packages/contracts`.
- Docker Compose stack: postgres (pgvector), redis, minio, api, worker, beat, voice, web, caddy.
- Lint/typecheck/test wired for every app; CI green.
- OTP login (Twilio Verify + `DEMO_MODE` fixed OTP) with JWT cookies, RBAC + region scoping,
  hash-chained audit trail, demo clock, transactional-outbox → SSE live notifications.
- Design system: tokens, light/dark/system theming, 6-locale i18n (en/hi/te/ml/ta/kn), shared
  shell + status components, a role-gated page per role, `/dev/components` gallery.

Workflow engine, applications, documents, EVC, committee, compliance tracking, messaging, voice
integration, dashboards, admin config, AI features, and hardening land in Phases P2–P12.

## Prerequisites

- [pnpm](https://pnpm.io) ≥ 9, Node ≥ 20
- [uv](https://docs.astral.sh/uv/) (Python 3.12 project/dependency manager)
- Docker + Docker Compose

## Local development

```bash
cp .env.example .env   # fill in real secrets for anything you actually need (Twilio, LLM, ...)

# Everything via Docker Compose:
docker compose -f infra/docker-compose.yml up --build
# dev mode (live reload, bind-mounted source):
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up --build
```

Or run each app natively:

```bash
pnpm install
pnpm --filter web dev          # http://localhost:3000

cd apps/api && uv sync && uv run uvicorn app.main:app --reload   # http://localhost:8000/api/v1/health
cd apps/voice && uv sync && uv run uvicorn app.main:app --reload --port 8010   # http://localhost:8010/health

# Background jobs (outbox -> SSE, deadline scanner from P7 onward):
cd apps/api && uv run celery -A app.workers.celery_app.celery_app worker -l info --pool=solo
#                                                                          ^^^^^^^^^^^^^^^^
# --pool=solo works around a macOS + Python 3.12 multiprocessing issue with Celery's
# default prefork pool (fork() under spawn-start-method). Not needed in Docker/Linux.
cd apps/api && uv run celery -A app.workers.celery_app.celery_app beat -l info

# Seed demo data (one region/institution + one user per role):
cd apps/api && uv run python -m app.seed
```

Exposing `api`/`voice` to Twilio webhooks during local dev:

```bash
pnpm tunnel   # cloudflared quick tunnel, routes /api/* and /voice/* per infra/Caddyfile
```

## Quality gates

```bash
pnpm turbo run lint typecheck test   # apps/web
cd apps/api && uv run ruff check . && uv run mypy app && uv run pytest -q
cd apps/voice && uv run ruff check . && uv run mypy app && uv run pytest -q
```

## Repo layout

See `IMPLEMENTATION.md` §5 for the full annotated tree. Top level:

```
apps/web/        Next.js — all role portals + EVC PWA   (Track P)
apps/api/        FastAPI core API, workflow/SLA/notification engines, AI services   (Track P)
apps/voice/      FastAPI AI calling agent service (Twilio Voice)   (Track V)
packages/contracts/   Shared OpenAPI spec, JSON schemas, generated TS client
infra/           Docker Compose, Caddyfile, postgres init
docs/            CHANGELOG, DECISIONS log, demo script
data/            APH source PDFs (manual download) + seed data
```

## Demo accounts

After `uv run python -m app.seed` (or `pnpm seed` from the repo root), with `DEMO_MODE=true`
(the `.env.example` default) every account below accepts OTP **`123456`**:

| Role | Phone |
|---|---|
| `ADMIN` | `+911000000001` |
| `BUREAU_HEAD` | `+911000000002` |
| `REGIONAL_OFFICER` | `+911000000003` |
| `SCRUTINY_OFFICER` | `+911000000004` |
| `COMMITTEE_MEMBER` | `+911000000005` |
| `EVC_EXPERT` | `+911000000006` |
| `INSTITUTION` | `+911000000007` |

Log in at `/login`, pick the role tab, enter the phone number, then the OTP above.

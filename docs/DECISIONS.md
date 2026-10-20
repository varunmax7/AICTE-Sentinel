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
- **Audit-only DB role**: `infra/postgres/init.sql` creates the `vector` and `pgcrypto`
  extensions on the main `acp` database. The audit-only role (`INSERT, SELECT` only on
  `audit_events`, per §16) is granted by a post-migration script
  (`apps/api/scripts/grant_audit_role.sql`) rather than in `init.sql`, because the `audit_events`
  table does not exist until the P1 migration runs — `init.sql` only runs once, before any
  migration, on first container start.
- **Secrets**: `.env.example` is committed verbatim from §6; a local `.env` (gitignored) must be
  created by each developer (`cp .env.example .env`) before `docker compose up`.
- **Linting**: `ruff` + `mypy` for both Python apps (shared `pyproject.toml` tool config per app,
  not a shared root config, since `apps/api` and `apps/voice` have independent dependency sets).

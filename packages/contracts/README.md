# @aicte-acp/contracts

Shared contract artifacts between `apps/web`, `apps/api` and `apps/voice` (IMPLEMENTATION.md §5).

| File | Produced by | Phase |
|---|---|---|
| `openapi.json` | `pnpm contracts:export` (exports the live FastAPI schema from `apps/api`) | P0 (CI step), grows every phase |
| `ts/api.d.ts` | `pnpm contracts:gen` (generated from `openapi.json` via `openapi-typescript`) | P0 (CI step), grows every phase |
| `voice-tools.json` | Hand-authored tool schema shared with `apps/voice` | P8 / V2–V3 (§12.5) |
| `workflow-rule.schema.json` | Hand-authored JSON Schema for `workflow_rules.definition` | P2 (§9.2) |
| `escalation-policy.schema.json` | Hand-authored JSON Schema for `escalation_policies.definition` | P7 (§10.2) |

`openapi.json` and `ts/` are regenerated, not hand-edited — see `.gitignore` (the generated
`ts/*.d.ts` files are not committed; CI regenerates them). `voice-tools.json` and the two
`*.schema.json` files are authored by hand once the corresponding phase defines them.

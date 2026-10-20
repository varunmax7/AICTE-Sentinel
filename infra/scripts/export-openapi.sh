#!/usr/bin/env bash
# Exports the FastAPI app's live OpenAPI schema to packages/contracts/openapi.json.
# Run from the repo root: `pnpm contracts:export` (or `bash infra/scripts/export-openapi.sh`).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

(
  cd "$repo_root/apps/api"
  uv run python -c "
import json
from app.main import app

with open('$repo_root/packages/contracts/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
    f.write('\n')
"
)

echo "Exported OpenAPI schema -> packages/contracts/openapi.json"

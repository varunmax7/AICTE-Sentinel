#!/usr/bin/env node
// Generates a typed TS client (packages/contracts/ts/api.d.ts) from
// packages/contracts/openapi.json, for use by apps/web's openapi-fetch client
// (IMPLEMENTATION.md §3, §5). Run `pnpm contracts:export` first to produce
// openapi.json from the live FastAPI app.
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const specPath = join(root, "openapi.json");
const outDir = join(root, "ts");
const outFile = join(outDir, "api.d.ts");

if (!existsSync(specPath)) {
  console.log("[contracts:gen] openapi.json not found — run `pnpm contracts:export` first.");
  process.exit(0);
}

const ast = await openapiTS(new URL(`file://${specPath}`));
mkdirSync(outDir, { recursive: true });
writeFileSync(outFile, astToString(ast));
console.log(`[contracts:gen] wrote ${outFile}`);

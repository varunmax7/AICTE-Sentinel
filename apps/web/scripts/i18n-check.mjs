#!/usr/bin/env node
// Fails CI if any message key present in the `en` locale is missing from the other
// 5 locales (IMPLEMENTATION.md §8). Until Phase P1 creates `messages/*.json`, this
// script is a no-op placeholder so `turbo run i18n:check` stays green in CI.
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const messagesDir = join(here, "..", "messages");
const locales = ["en", "hi", "te", "ml", "ta", "kn"];

if (!existsSync(messagesDir)) {
  console.log("[i18n:check] messages/ not created yet (Phase P1) — skipping.");
  process.exit(0);
}

function flatten(obj, prefix = "") {
  return Object.entries(obj).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return flatten(value, path);
    }
    return [path];
  });
}

const enPath = join(messagesDir, "en.json");
if (!existsSync(enPath)) {
  console.error("[i18n:check] messages/en.json is missing.");
  process.exit(1);
}
const enKeys = new Set(flatten(JSON.parse(readFileSync(enPath, "utf8"))));

let failed = false;
for (const locale of locales.filter((l) => l !== "en")) {
  const localePath = join(messagesDir, `${locale}.json`);
  if (!existsSync(localePath)) {
    console.error(`[i18n:check] messages/${locale}.json is missing.`);
    failed = true;
    continue;
  }
  const keys = new Set(flatten(JSON.parse(readFileSync(localePath, "utf8"))));
  const missing = [...enKeys].filter((k) => !keys.has(k));
  if (missing.length > 0) {
    console.error(`[i18n:check] ${locale}.json missing ${missing.length} key(s): ${missing.slice(0, 10).join(", ")}${missing.length > 10 ? ", ..." : ""}`);
    failed = true;
  }
}

if (failed) process.exit(1);
console.log(`[i18n:check] OK — all locales (${locales.join(", ")}) have the same keys as en.`);

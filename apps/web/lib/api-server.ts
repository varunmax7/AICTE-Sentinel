import { cookies } from "next/headers";

import type { MeOut } from "./api";

const API_BASE = process.env.PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Generic server-side GET against the core API, forwarding the incoming
 * request's cookies (see `getServerMe` below for why). Returns `null` on any
 * non-2xx response — callers that need to distinguish 404 from "unauthenticated"
 * should call the client-side `api` helpers (which throw `ApiError`) instead.
 */
export async function apiServerGet<T>(path: string): Promise<T | null> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  if (!cookieHeader) return null;

  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Cookie: cookieHeader },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as T;
}

/**
 * Server-side `/me` fetch for layouts/pages (Server Components), forwarding
 * the incoming request's cookies manually since this is a server-to-server
 * fetch, not a browser one (so no CORS, but also no automatic cookie jar).
 * Returns null if unauthenticated — callers that need a user should rely on
 * `middleware.ts` having already redirected unauthenticated requests away;
 * this is for reading the profile, not enforcing access.
 */
export async function getServerMe(): Promise<MeOut | null> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.toString();
  if (!cookieHeader) return null;

  const res = await fetch(`${API_BASE}/api/v1/me`, {
    headers: { Cookie: cookieHeader },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as MeOut;
}

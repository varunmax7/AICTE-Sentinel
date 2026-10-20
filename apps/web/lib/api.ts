/**
 * Minimal typed fetch wrapper for the core API (IMPLEMENTATION.md §13).
 * Always sends cookies (`credentials: "include"`) since auth is httpOnly
 * JWT cookies, not a bearer token the client holds. Errors are normalized
 * to the `{ error: { code, params } }` envelope the backend returns
 * (`app.core.errors`) so callers can translate `error.code` via i18n.
 *
 * A fuller typed client (openapi-fetch generated from
 * packages/contracts/openapi.json, per §3/§5) replaces this once enough of
 * the API surface exists to make codegen worthwhile — this hand-written
 * version covers Phase P1's auth/me/clock endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  params: Record<string, unknown>;
  status: number;

  constructor(status: number, code: string, params: Record<string, unknown> = {}) {
    super(code);
    this.status = status;
    this.code = code;
    this.params = params;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let code = "HTTP_ERROR";
    let params: Record<string, unknown> = { status: res.status };
    try {
      const body = await res.json();
      if (body?.error?.code) {
        code = body.error.code;
        params = body.error.params ?? {};
      }
    } catch {
      // response had no JSON body — keep the generic HTTP_ERROR code
    }
    throw new ApiError(res.status, code, params);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
};

// ---------------------------------------------------------------------------
// Types used by Phase P1 screens
// ---------------------------------------------------------------------------

export type UserRole =
  | "INSTITUTION"
  | "SCRUTINY_OFFICER"
  | "REGIONAL_OFFICER"
  | "BUREAU_HEAD"
  | "COMMITTEE_MEMBER"
  | "EVC_EXPERT"
  | "ADMIN";

export interface RegionOut {
  id: string;
  code: string;
  name: string;
}

export interface MeOut {
  id: string;
  name: string;
  role: UserRole;
  preferred_language: string;
  theme: "light" | "dark" | "system";
  institution_id: string | null;
  regions: RegionOut[];
}

export function sendOtp(identifier: string, role: UserRole) {
  return api.post<{ sent: boolean; expires_in_seconds: number }>("/api/v1/auth/otp/send", {
    identifier,
    role,
  });
}

export function verifyOtp(identifier: string, role: UserRole, code: string) {
  return api.post<MeOut>("/api/v1/auth/otp/verify", { identifier, role, code });
}

export function logout() {
  return api.post<{ ok: boolean }>("/api/v1/auth/logout");
}

export function getMe() {
  return api.get<MeOut>("/api/v1/me");
}

export function updateMe(body: Partial<Pick<MeOut, "name" | "preferred_language" | "theme">>) {
  return api.patch<MeOut>("/api/v1/me", body);
}

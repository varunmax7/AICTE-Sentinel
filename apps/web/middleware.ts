import createMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";

import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);

/** Role -> its sidebar home, per IMPLEMENTATION.md §15. */
const ROLE_HOME: Record<string, string> = {
  INSTITUTION: "/institution/dashboard",
  SCRUTINY_OFFICER: "/officer/dashboard",
  REGIONAL_OFFICER: "/regional/dashboard",
  BUREAU_HEAD: "/bureau/dashboard",
  COMMITTEE_MEMBER: "/committee/dashboard",
  EVC_EXPERT: "/expert",
  ADMIN: "/admin/dashboard",
};

const PROTECTED_SEGMENTS = new Set(
  Object.values(ROLE_HOME).map((path) => path.split("/")[1])
);

/** First path segment -> the one role allowed in it (reverse of ROLE_HOME). */
const SEGMENT_TO_ROLE: Record<string, string> = Object.fromEntries(
  Object.entries(ROLE_HOME).map(([role, home]) => [home.split("/")[1], role])
);

/**
 * Reads the `role` claim out of the access-token JWT WITHOUT verifying its
 * signature. This is a UX redirect only (send a logged-out visitor to
 * /login, send a logged-in one away from /login to their role home) — it is
 * NOT a security boundary. The actual authorization check happens on every
 * API request in `app.core.deps.get_current_user` (apps/api), which does
 * verify the signature. Middleware runs in the Edge runtime, where verifying
 * HS256 would need an extra dependency (`jose`) for no real security benefit
 * here, since a forged cookie would still be rejected by the API.
 */
function readRoleUnverified(token: string | undefined): string | null {
  if (!token) return null;
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const json = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8")
    ) as { role?: string; exp?: number };
    if (typeof json.exp === "number" && json.exp * 1000 < Date.now()) return null;
    return json.role ?? null;
  } catch {
    return null;
  }
}

export default function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const localeMatch = pathname.match(/^\/([a-z]{2})(\/.*)?$/);
  const locale = localeMatch?.[1] ?? routing.defaultLocale;
  const pathWithoutLocale = localeMatch ? localeMatch[2] ?? "/" : pathname;

  const role = readRoleUnverified(request.cookies.get("acp_access")?.value);
  const firstSegment = pathWithoutLocale.split("/")[1] ?? "";
  const isProtected = PROTECTED_SEGMENTS.has(firstSegment);
  const isLogin = pathWithoutLocale.startsWith("/login");

  if (isProtected && !role) {
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}/login`;
    return NextResponse.redirect(url);
  }

  // A role may only browse its own segment — e.g. a SCRUTINY_OFFICER hitting
  // /admin/* gets sent to their own home rather than seeing the admin shell.
  if (isProtected && role && SEGMENT_TO_ROLE[firstSegment] !== role) {
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}${ROLE_HOME[role] ?? "/login"}`;
    return NextResponse.redirect(url);
  }

  if (isLogin && role) {
    const home = ROLE_HOME[role] ?? "/login";
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}${home}`;
    return NextResponse.redirect(url);
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};

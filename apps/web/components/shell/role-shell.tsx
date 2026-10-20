import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { redirect } from "@/i18n/navigation";
import { getServerMe } from "@/lib/api-server";

import { Shell } from "./shell";

/**
 * Shared layout body for every role segment: fetches `/me` server-side and
 * renders the Shell with that role's sidebar. `middleware.ts` already
 * redirects an unauthenticated request before it gets here — this redirect
 * is the defensive fallback (e.g. the access cookie expired between the
 * middleware check and this render).
 */
export async function RoleShell({
  children,
  settingsPath,
}: {
  children: ReactNode;
  settingsPath: string;
}) {
  const me = await getServerMe();
  if (!me) {
    redirect({ href: "/login", locale: await getLocale() });
    return null;
  }

  return (
    <Shell me={me} settingsHref={settingsPath}>
      {children}
    </Shell>
  );
}

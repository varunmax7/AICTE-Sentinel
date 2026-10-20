import { getLocale } from "next-intl/server";

import { redirect } from "@/i18n/navigation";
import { getServerMe } from "@/lib/api-server";

/**
 * The EVC expert PWA (IMPLEMENTATION.md §15.6, §7.1) is mobile-first and
 * dark-by-default with its own navigation paradigm — no TopBar/Sidebar
 * shell. The full inspect/checklist/camera flow is Phase P4; this is the
 * Phase P1 "land on role home" placeholder.
 */
export default async function ExpertHomePage() {
  const me = await getServerMe();
  if (!me) {
    redirect({ href: "/login", locale: await getLocale() });
  }

  return (
    <main
      data-theme="dark"
      className="flex min-h-screen flex-col items-center justify-center gap-3 bg-bg p-6 text-center text-text"
    >
      <h1 className="text-lg font-semibold">Welcome, {me?.name}</h1>
      <p className="max-w-sm text-sm text-muted">
        The EVC expert inspection app (geotagged photos, offline checklist, dictation) is built in
        Phase P4.
      </p>
    </main>
  );
}

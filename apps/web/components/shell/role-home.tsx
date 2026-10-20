import { getTranslations } from "next-intl/server";

import { getServerMe } from "@/lib/api-server";

/** Generic role-home placeholder — each role's real dashboard lands in its own phase. */
export async function RoleHome() {
  const me = await getServerMe();
  if (!me) return null;

  const t = await getTranslations("roleHome");
  const tAuth = await getTranslations("auth");
  const tCommon = await getTranslations("common");

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-xl font-semibold text-text">{t("greeting", { name: me.name })}</h1>
      <p className="mt-1 text-sm text-muted">
        {t("role", { role: tAuth(`roles.${me.role}` as Parameters<typeof tAuth>[0]) })}
      </p>
      <p className="mt-6 rounded-xl border border-dashed border-border bg-surface-2 p-6 text-sm text-muted">
        {tCommon("comingSoon")}
      </p>
    </div>
  );
}

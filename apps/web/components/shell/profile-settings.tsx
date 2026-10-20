"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import type { MeOut } from "@/lib/api";
import { updateMe } from "@/lib/api";

import { ThemeToggle } from "../theme/theme-toggle";
import { Button } from "../ui/button";
import { LanguageSwitcher } from "./language-switcher";

/** `/settings` (IMPLEMENTATION.md §15.1): language, theme, name. */
export function ProfileSettings({ me }: { me: MeOut }) {
  const t = useTranslations("settings");
  const tCommon = useTranslations("common");
  const [name, setName] = useState(me.name);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await updateMe({ name });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-lg p-4 md:p-6">
      <h1 className="text-xl font-semibold text-text">{t("title")}</h1>

      <form onSubmit={handleSave} className="mt-6 space-y-5">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-muted">{t("name")}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>

        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">{t("language")}</span>
          <LanguageSwitcher />
        </div>

        <div>
          <span className="mb-1.5 block text-xs font-medium text-muted">{t("theme")}</span>
          <ThemeToggle />
        </div>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={loading}>
            {tCommon("save")}
          </Button>
          {saved && <span className="text-sm text-success">{t("saved")}</span>}
        </div>
      </form>
    </div>
  );
}

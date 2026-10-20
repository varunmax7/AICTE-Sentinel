"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "light", icon: Sun, labelKey: "themeLight" as const },
  { value: "dark", icon: Moon, labelKey: "themeDark" as const },
  { value: "system", icon: Laptop, labelKey: "themeSystem" as const },
];

export function ThemeToggle() {
  const t = useTranslations("common");
  const { theme, setTheme } = useTheme();
  // Avoid a hydration mismatch: the server doesn't know the stored theme yet.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <div
      className="flex items-center gap-0.5 rounded-full border border-border bg-surface-2 p-0.5"
      role="radiogroup"
      aria-label={t("theme")}
    >
      {OPTIONS.map(({ value, icon: Icon, labelKey }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mounted && theme === value}
          title={t(labelKey)}
          onClick={() => setTheme(value)}
          className={cn(
            "rounded-full p-1.5 text-muted transition-colors hover:text-text",
            mounted && theme === value && "bg-surface text-text shadow-sm"
          )}
        >
          <Icon className="size-4" aria-hidden />
          <span className="sr-only">{t(labelKey)}</span>
        </button>
      ))}
    </div>
  );
}

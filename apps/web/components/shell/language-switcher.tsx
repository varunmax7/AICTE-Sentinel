"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Languages } from "lucide-react";
import { useLocale } from "next-intl";

import { usePathname, useRouter } from "@/i18n/navigation";
import { locales } from "@/i18n/routing";

const LABELS: Record<string, string> = {
  en: "English",
  hi: "हिन्दी",
  te: "తెలుగు",
  ml: "മലയാളം",
  ta: "தமிழ்",
  kn: "ಕನ್ನಡ",
};

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1.5 text-sm text-text hover:bg-surface"
          aria-label="Change language"
        >
          <Languages className="size-4" aria-hidden />
          {LABELS[locale]}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-36 rounded-xl border border-border bg-surface p-1 shadow-lg"
        >
          {locales.map((code) => (
            <DropdownMenu.Item
              key={code}
              onSelect={() => router.replace(pathname, { locale: code })}
              className="cursor-pointer rounded-lg px-3 py-2 text-sm text-text outline-none data-[highlighted]:bg-surface-2"
            >
              {LABELS[code]}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

import { Mail, MessageCircle, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Link } from "@/i18n/navigation";
import type { MeOut } from "@/lib/api";

import { ThemeToggle } from "../theme/theme-toggle";
import { IconBadge } from "../status/icon-badge";
import { LanguageSwitcher } from "./language-switcher";
import { NotificationCenter } from "./notification-center";
import { ProfileMenu } from "./profile-menu";

/**
 * 72px navy top bar (IMPLEMENTATION.md §7.1/§7.4). The emblem/AICTE logo is a
 * placeholder icon here — `public/brand/` assets are team-provided and not
 * fabricated by this scaffold (see §7.4).
 */
export function TopBar({
  me,
  settingsHref,
  slaSlot,
}: {
  me: MeOut;
  settingsHref: string;
  slaSlot?: ReactNode;
}) {
  const t = useTranslations("common");

  return (
    <header className="flex h-[72px] shrink-0 items-center gap-4 bg-topbar px-4 text-topbar-fg md:px-6">
      <Link href="/" className="flex shrink-0 items-center gap-2.5">
        <span className="flex size-8 items-center justify-center rounded-full bg-white/10">
          <ShieldCheck className="size-[18px]" aria-hidden />
        </span>
        <span className="hidden flex-col leading-tight sm:flex">
          <span className="text-[11px] uppercase tracking-wide text-topbar-fg/70">
            All India Council for Technical Education
          </span>
          <span className="text-sm font-semibold">{t("appFullName")}</span>
        </span>
      </Link>

      <div className="hidden flex-1 justify-center lg:flex">
        <input
          type="search"
          placeholder={t("search")}
          className="w-full max-w-[520px] rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-topbar-fg placeholder:text-topbar-fg/50 focus:outline-none focus:ring-2 focus:ring-white/30"
        />
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        {slaSlot}
        <IconBadge icon={Mail} label="Mail" />
        <IconBadge icon={MessageCircle} label="WhatsApp" />
        <NotificationCenter />
        <div className="mx-1 hidden sm:block">
          <LanguageSwitcher />
        </div>
        <ThemeToggle />
        <ProfileMenu me={me} settingsHref={settingsHref} />
      </div>
    </header>
  );
}

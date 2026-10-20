"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Link, usePathname } from "@/i18n/navigation";
import type { UserRole } from "@/lib/api";
import { NAV_BY_ROLE } from "@/lib/nav-config";
import { cn } from "@/lib/utils";

/**
 * 240px, collapsible to 72px; active item gets a left accent bar (§7.4).
 * Takes `role` (a plain string) rather than resolved `NavItem[]` — lucide
 * icon components can't cross the Server->Client Component boundary as
 * props, so this Client Component resolves `NAV_BY_ROLE` itself instead of
 * receiving it pre-resolved from the server-rendered `RoleShell`.
 */
export function Sidebar({ role }: { role: UserRole }) {
  const t = useTranslations("nav");
  const tCommon = useTranslations("common");
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const items = NAV_BY_ROLE[role];

  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] md:flex",
        collapsed ? "w-[72px]" : "w-[240px]"
      )}
    >
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {items.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <li key={item.key}>
                <Link
                  href={item.href}
                  className={cn(
                    "relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-text",
                    active && "bg-surface-2 font-medium text-text"
                  )}
                >
                  {active && (
                    <span className="absolute -left-2 top-1/2 h-5 -translate-y-1/2 rounded-full bg-primary" style={{ width: 3 }} />
                  )}
                  <Icon className="size-[18px] shrink-0" aria-hidden />
                  {!collapsed && <span className="truncate">{t(item.key)}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="flex items-center justify-between gap-2 border-t border-border p-2">
        {!collapsed && <span className="px-2 text-[11px] text-muted">{tCommon("version")}</span>}
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex shrink-0 items-center justify-center rounded-lg p-2 text-muted hover:bg-surface-2 hover:text-text"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight className="size-4" /> : <ChevronLeft className="size-4" />}
        </button>
      </div>
    </aside>
  );
}

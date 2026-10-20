import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { Link } from "@/i18n/navigation";

export interface Crumb {
  label: string;
  href?: string;
}

/** "Queue › SCR-402 › APP-2026-0451" (IMPLEMENTATION.md §7.1). */
export function Breadcrumbs({ items, trailing }: { items: Crumb[]; trailing?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 md:px-6">
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-muted">
        {items.map((item, i) => (
          <span key={`${item.label}-${i}`} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="size-3.5" aria-hidden />}
            {item.href ? (
              <Link href={item.href} className="hover:text-text">
                {item.label}
              </Link>
            ) : (
              <span className="text-text">{item.label}</span>
            )}
          </span>
        ))}
      </nav>
      {trailing}
    </div>
  );
}

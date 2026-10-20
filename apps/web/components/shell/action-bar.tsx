import type { ReactNode } from "react";

/** Sticky bottom action bar (IMPLEMENTATION.md §7.4) — case-page buttons go here. */
export function ActionBar({ children }: { children: ReactNode }) {
  return (
    <div className="sticky bottom-0 z-10 flex h-[72px] shrink-0 items-center justify-between gap-3 border-t border-border bg-surface px-4 md:px-6">
      <span className="hidden text-xs font-medium tracking-wide text-muted sm:inline">AICTE GOV.IN</span>
      <div className="flex flex-1 items-center justify-end gap-2">{children}</div>
    </div>
  );
}

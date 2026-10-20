import type { LucideIcon } from "lucide-react";
import { Clock } from "lucide-react";

import { cn } from "@/lib/utils";

export interface TimelineEntry {
  id: string;
  actor: string;
  action: string;
  at: string;
  channel?: string;
  icon?: LucideIcon;
}

/** Vertical event list with actor, time, icon, channel (IMPLEMENTATION.md §7.5). */
export function Timeline({ entries, className }: { entries: TimelineEntry[]; className?: string }) {
  return (
    <ol className={cn("relative space-y-0", className)}>
      {entries.map((entry, i) => {
        const Icon = entry.icon ?? Clock;
        return (
          <li key={entry.id} className="relative flex gap-3 pb-6 last:pb-0">
            {i < entries.length - 1 && (
              <span className="absolute left-[15px] top-8 h-[calc(100%-1.75rem)] w-px bg-border" aria-hidden />
            )}
            <span className="z-10 flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-surface">
              <Icon className="size-4 text-muted" aria-hidden />
            </span>
            <div className="flex-1 pt-1">
              <p className="text-sm text-text">
                <span className="font-medium">{entry.actor}</span> {entry.action}
              </p>
              <p className="mt-0.5 text-xs text-muted">
                {new Date(entry.at).toLocaleString()}
                {entry.channel ? ` · ${entry.channel}` : ""}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

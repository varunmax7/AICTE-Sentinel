"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Purple "AI" chip, used everywhere an AI output is shown — a draft/
 * suggestion/flag the IMPLEMENTATION.md §1.3 regulatory safeguard requires a
 * human to confirm before it takes effect.
 */
export function AiBadge({ className }: { className?: string }) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full bg-ai-soft px-2 py-0.5 text-xs font-medium text-ai",
              className
            )}
          >
            <Sparkles className="size-3" aria-hidden />
            AI
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            sideOffset={6}
            className="z-50 max-w-56 rounded-lg bg-text px-2.5 py-1.5 text-xs text-bg shadow-lg"
          >
            AI-generated — verify before use
            <Tooltip.Arrow className="fill-text" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

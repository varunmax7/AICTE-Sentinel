import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import type { StageInstanceOut } from "@/lib/api";

const TONE: Record<StageInstanceOut["status"], string> = {
  COMPLETED: "border-success bg-success-soft text-success",
  ACTIVE: "border-primary bg-ai-soft text-primary",
  RETURNED: "border-warning bg-warning-soft text-warning",
  REFERRED: "border-warning bg-warning-soft text-warning",
  PENDING: "border-border text-muted",
  SKIPPED: "border-border text-muted opacity-50",
};

/** Horizontal stage stepper for the application-detail header (IMPLEMENTATION.md §15.2). */
export function StageStepper({ stages }: { stages: StageInstanceOut[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 overflow-x-auto">
      {stages.map((stage, i) => (
        <li key={stage.id} className="flex items-center gap-2">
          <span
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
              TONE[stage.status]
            )}
          >
            {stage.status === "COMPLETED" && <Check className="size-3" aria-hidden />}
            {stage.stage_key}
          </span>
          {i < stages.length - 1 && <span className="h-px w-4 bg-border" aria-hidden />}
        </li>
      ))}
    </ol>
  );
}

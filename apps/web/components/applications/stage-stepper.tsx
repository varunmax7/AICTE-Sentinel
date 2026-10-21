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

/**
 * Horizontal variant for the application-detail header; vertical variant
 * for the Case Review Workspace's CaseFilePanel (IMPLEMENTATION.md §7.5,
 * §15.2/§15.3).
 */
export function StageStepper({
  stages,
  orientation = "horizontal",
}: {
  stages: StageInstanceOut[];
  orientation?: "horizontal" | "vertical";
}) {
  if (orientation === "vertical") {
    return (
      <ol className="space-y-0">
        {stages.map((stage, i) => (
          <li key={stage.id} className="relative flex gap-3 pb-6 last:pb-0">
            {i < stages.length - 1 && (
              <span className="absolute left-[11px] top-6 h-[calc(100%-1rem)] w-px bg-border" aria-hidden />
            )}
            <span
              className={cn(
                "z-10 flex size-6 shrink-0 items-center justify-center rounded-full border text-[10px]",
                TONE[stage.status]
              )}
            >
              {stage.status === "COMPLETED" ? <Check className="size-3" aria-hidden /> : i + 1}
            </span>
            <div className="pt-0.5">
              <p className="text-sm font-medium text-text">{stage.stage_key}</p>
              <p className="text-xs text-muted">{stage.status}</p>
            </div>
          </li>
        ))}
      </ol>
    );
  }

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

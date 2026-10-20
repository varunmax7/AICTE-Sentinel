import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

export type AppStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "IN_PROCESS"
  | "DECISION_RECORDED"
  | "APPROVED"
  | "APPROVED_WITH_CONDITIONS"
  | "REJECTED"
  | "WITHDRAWN"
  | "PENDING"
  | "ACTIVE"
  | "COMPLETED"
  | "RETURNED"
  | "REFERRED"
  | "SKIPPED";

const TONE: Record<AppStatus, string> = {
  DRAFT: "bg-surface-2 text-muted border-border",
  SUBMITTED: "bg-ai-soft text-ai border-transparent",
  IN_PROCESS: "bg-ai-soft text-ai border-transparent",
  ACTIVE: "bg-ai-soft text-ai border-transparent",
  PENDING: "bg-warning-soft text-warning border-transparent",
  RETURNED: "bg-warning-soft text-warning border-transparent",
  REFERRED: "bg-warning-soft text-warning border-transparent",
  DECISION_RECORDED: "bg-success-soft text-success border-transparent",
  APPROVED: "bg-success-soft text-success border-transparent",
  APPROVED_WITH_CONDITIONS: "bg-success-soft text-success border-transparent",
  COMPLETED: "bg-success-soft text-success border-transparent",
  REJECTED: "bg-danger-soft text-danger border-transparent",
  WITHDRAWN: "bg-surface-2 text-muted border-border",
  SKIPPED: "bg-surface-2 text-muted border-border",
};

export function StatusChip({ status, className }: { status: AppStatus; className?: string }) {
  const t = useTranslations("status");
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        TONE[status],
        className
      )}
    >
      {t(status)}
    </span>
  );
}

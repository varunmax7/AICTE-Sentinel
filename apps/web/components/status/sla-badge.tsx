import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

export type SlaState = "on-time" | "due-soon" | "overdue";

export function slaState(daysLeft: number): SlaState {
  if (daysLeft < 0) return "overdue";
  if (daysLeft <= 3) return "due-soon";
  return "on-time";
}

const DOT: Record<SlaState, string> = {
  "on-time": "bg-success",
  "due-soon": "bg-warning",
  overdue: "bg-danger",
};

const TEXT: Record<SlaState, string> = {
  "on-time": "text-success",
  "due-soon": "text-warning",
  overdue: "text-danger",
};

/** 🟢 on-time / 🟡 due ≤3 days / 🔴 overdue + "N days" (IMPLEMENTATION.md §7.5). */
export function SlaBadge({ dueAt, now, className }: { dueAt: string | Date; now?: Date; className?: string }) {
  const t = useTranslations("sla");
  const due = new Date(dueAt);
  const reference = now ?? new Date();
  const daysLeft = Math.ceil((due.getTime() - reference.getTime()) / (1000 * 60 * 60 * 24));
  const state = slaState(daysLeft);

  const label =
    state === "overdue"
      ? t("overdue", { days: Math.abs(daysLeft) })
      : state === "due-soon"
        ? t("dueSoon", { days: daysLeft })
        : t("onTime", { days: daysLeft });

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", TEXT[state], className)}>
      <span className={cn("size-1.5 rounded-full", DOT[state])} aria-hidden />
      {label}
    </span>
  );
}

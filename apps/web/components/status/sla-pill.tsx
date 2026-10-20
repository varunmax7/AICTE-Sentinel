import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";
import { slaState } from "./sla-badge";

/**
 * Gold gradient pill bound to the current case's stage deadline, shown in
 * the top bar on case pages (IMPLEMENTATION.md §7.1/§7.4): "{n} Days Left
 * (On-Time)" / amber "Due Soon" / red "{n} Days Overdue".
 */
export function SlaPill({ dueAt, now, className }: { dueAt: string | Date; now?: Date; className?: string }) {
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
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold text-white shadow-sm",
        state === "on-time" && "bg-gradient-to-r from-[var(--gold-1)] to-[var(--gold-2)]",
        state === "due-soon" && "bg-warning",
        state === "overdue" && "bg-danger",
        className
      )}
    >
      {label}
    </span>
  );
}

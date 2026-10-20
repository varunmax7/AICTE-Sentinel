import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  icon: Icon,
  tone = "default",
  className,
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  tone?: "default" | "success" | "warning" | "danger";
  className?: string;
}) {
  const toneText = {
    default: "text-text",
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  }[tone];

  return (
    <div className={cn("rounded-2xl border border-border bg-surface p-4", className)}>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{label}</p>
        {Icon && <Icon className="size-4 text-muted" aria-hidden />}
      </div>
      <p className={cn("mt-2 text-2xl font-semibold", toneText)}>{value}</p>
    </div>
  );
}

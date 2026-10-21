import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const TONE = {
  PASS: { border: "border-success/30", bg: "bg-success-soft", text: "text-success", Icon: CheckCircle2 },
  WARN: { border: "border-warning/30", bg: "bg-warning-soft", text: "text-warning", Icon: AlertTriangle },
  FAIL: { border: "border-danger/30", bg: "bg-danger-soft", text: "text-danger", Icon: XCircle },
} as const;

/** AI panel check card: icon + title + status tag + body (IMPLEMENTATION.md §7.5). */
export function CheckCard({
  title,
  status,
  children,
  className,
}: {
  title: string;
  status: "PASS" | "WARN" | "FAIL";
  children?: ReactNode;
  className?: string;
}) {
  const tone = TONE[status];
  const Icon = tone.Icon;
  return (
    <div className={cn("rounded-xl border p-3", tone.border, tone.bg, className)}>
      <div className="flex items-center gap-2">
        <Icon className={cn("size-4 shrink-0", tone.text)} aria-hidden />
        <p className="text-sm font-medium text-text">{title}</p>
        <span className={cn("ml-auto shrink-0 text-xs font-semibold", tone.text)}>{status}</span>
      </div>
      {children && <div className="mt-1.5 text-xs text-muted">{children}</div>}
    </div>
  );
}

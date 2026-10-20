import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** Icon + count bubble — top bar mail/WhatsApp/bell (IMPLEMENTATION.md §7.4/§7.5). */
export function IconBadge({
  icon: Icon,
  count,
  label,
  onClick,
  className,
}: {
  icon: LucideIcon;
  count?: number;
  label: string;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={cn(
        "relative inline-flex size-9 items-center justify-center rounded-full text-topbar-fg/80 transition-colors hover:bg-white/10 hover:text-topbar-fg",
        className
      )}
    >
      <Icon className="size-[18px]" aria-hidden />
      {!!count && count > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex min-w-[18px] items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-[18px] text-white">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </button>
  );
}

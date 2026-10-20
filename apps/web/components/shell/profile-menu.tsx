"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { LogOut, Settings, User } from "lucide-react";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
import type { MeOut } from "@/lib/api";
import { logout } from "@/lib/api";

export function ProfileMenu({ me, settingsHref }: { me: MeOut; settingsHref: string }) {
  const t = useTranslations("auth");
  const router = useRouter();

  const initials = me.name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className="flex size-9 items-center justify-center rounded-full bg-white/10 text-sm font-semibold text-topbar-fg hover:bg-white/20"
          aria-label={me.name}
        >
          {initials || <User className="size-4" />}
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-50 min-w-48 rounded-xl border border-border bg-surface p-1 shadow-lg"
        >
          <div className="px-3 py-2">
            <p className="text-sm font-medium text-text">{me.name}</p>
            <p className="text-xs text-muted">{t(`roles.${me.role}`)}</p>
          </div>
          <DropdownMenu.Separator className="my-1 h-px bg-border" />
          <DropdownMenu.Item
            onSelect={() => router.push(settingsHref)}
            className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-text outline-none data-[highlighted]:bg-surface-2"
          >
            <Settings className="size-4" aria-hidden />
            Settings
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onSelect={async () => {
              await logout();
              router.push("/login");
            }}
            className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-danger outline-none data-[highlighted]:bg-danger-soft"
          >
            <LogOut className="size-4" aria-hidden />
            Sign out
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

import type { ReactNode } from "react";

import type { MeOut } from "@/lib/api";

import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";

/** TopBar + Sidebar shell every role page (except the expert PWA) renders inside. */
export function Shell({
  me,
  settingsHref,
  slaSlot,
  children,
}: {
  me: MeOut;
  settingsHref: string;
  slaSlot?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar me={me} settingsHref={settingsHref} slaSlot={slaSlot} />
      <div className="flex flex-1">
        <Sidebar role={me.role} />
        <main className="flex-1 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}

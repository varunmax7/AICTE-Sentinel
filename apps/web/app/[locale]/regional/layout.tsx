import { RoleShell } from "@/components/shell/role-shell";

export default function RegionalLayout({ children }: { children: React.ReactNode }) {
  return <RoleShell settingsPath="/regional/settings">{children}</RoleShell>;
}

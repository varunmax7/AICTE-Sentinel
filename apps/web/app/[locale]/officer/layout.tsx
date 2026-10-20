import { RoleShell } from "@/components/shell/role-shell";

export default function OfficerLayout({ children }: { children: React.ReactNode }) {
  return <RoleShell settingsPath="/officer/settings">{children}</RoleShell>;
}

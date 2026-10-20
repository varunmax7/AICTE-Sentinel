import { RoleShell } from "@/components/shell/role-shell";

export default function BureauLayout({ children }: { children: React.ReactNode }) {
  return <RoleShell settingsPath="/bureau/settings">{children}</RoleShell>;
}

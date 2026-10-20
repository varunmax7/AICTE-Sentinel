import { RoleShell } from "@/components/shell/role-shell";

export default function InstitutionLayout({ children }: { children: React.ReactNode }) {
  return <RoleShell settingsPath="/institution/settings">{children}</RoleShell>;
}

import { RoleShell } from "@/components/shell/role-shell";

export default function CommitteeLayout({ children }: { children: React.ReactNode }) {
  return <RoleShell settingsPath="/committee/settings">{children}</RoleShell>;
}

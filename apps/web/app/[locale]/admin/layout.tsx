import { RoleShell } from "@/components/shell/role-shell";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <RoleShell settingsPath="/admin/settings">{children}</RoleShell>;
}

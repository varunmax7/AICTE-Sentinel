import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  ClipboardCheck,
  Database,
  FileBarChart,
  FileText,
  FolderOpen,
  History,
  LayoutDashboard,
  type LucideIcon,
  Mail,
  MessageSquare,
  Phone,
  Settings,
  ShieldCheck,
  SquareCheckBig,
  TrendingUp,
  Users,
  Workflow,
} from "lucide-react";

import type { UserRole } from "./api";

export interface NavItem {
  key: string;
  href: string;
  icon: LucideIcon;
}

/** Sidebar items per role (IMPLEMENTATION.md §15). `key` is a `nav.*` message key. */
export const NAV_BY_ROLE: Record<UserRole, NavItem[]> = {
  INSTITUTION: [
    { key: "dashboard", href: "/institution/dashboard", icon: LayoutDashboard },
    { key: "applications", href: "/institution/applications", icon: FileText },
    { key: "compliance", href: "/institution/compliance", icon: ShieldCheck },
    { key: "documentVault", href: "/institution/vault", icon: FolderOpen },
    { key: "communications", href: "/institution/communications", icon: Mail },
    { key: "approvals", href: "/institution/approvals", icon: SquareCheckBig },
    { key: "settings", href: "/institution/settings", icon: Settings },
  ],
  SCRUTINY_OFFICER: [
    { key: "dashboard", href: "/officer/dashboard", icon: LayoutDashboard },
    { key: "queue", href: "/officer/queue", icon: ClipboardCheck },
    { key: "applications", href: "/officer/applications", icon: FileText },
    { key: "compliance", href: "/officer/compliance", icon: ShieldCheck },
    { key: "documentVault", href: "/officer/vault", icon: FolderOpen },
    { key: "analytics", href: "/officer/analytics", icon: BarChart3 },
    { key: "settings", href: "/officer/settings", icon: Settings },
  ],
  REGIONAL_OFFICER: [
    { key: "dashboard", href: "/regional/dashboard", icon: LayoutDashboard },
    { key: "pendency", href: "/regional/pendency", icon: TrendingUp },
    { key: "workload", href: "/regional/workload", icon: Users },
    { key: "escalations", href: "/regional/escalations", icon: AlertTriangle },
    { key: "evc", href: "/regional/evc", icon: ClipboardCheck },
    { key: "compliance", href: "/regional/compliance", icon: ShieldCheck },
    { key: "settings", href: "/regional/settings", icon: Settings },
  ],
  BUREAU_HEAD: [
    { key: "dashboard", href: "/bureau/dashboard", icon: LayoutDashboard },
    { key: "reports", href: "/bureau/reports", icon: FileBarChart },
    { key: "escalations", href: "/bureau/escalations", icon: AlertTriangle },
    { key: "analytics", href: "/bureau/analytics", icon: BarChart3 },
    { key: "settings", href: "/bureau/settings", icon: Settings },
  ],
  COMMITTEE_MEMBER: [
    { key: "dashboard", href: "/committee/dashboard", icon: LayoutDashboard },
    { key: "meetings", href: "/committee/meetings", icon: CalendarDays },
    { key: "settings", href: "/committee/settings", icon: Settings },
  ],
  EVC_EXPERT: [],
  ADMIN: [
    { key: "dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
    { key: "workflow", href: "/admin/workflow", icon: Workflow },
    { key: "escalationPolicies", href: "/admin/escalation", icon: AlertTriangle },
    { key: "templates", href: "/admin/templates", icon: MessageSquare },
    { key: "voice", href: "/admin/voice", icon: Phone },
    { key: "masterData", href: "/admin/master-data", icon: Database },
    { key: "audit", href: "/admin/audit", icon: History },
    { key: "health", href: "/admin/health", icon: Activity },
    { key: "settings", href: "/admin/settings", icon: Settings },
  ],
};

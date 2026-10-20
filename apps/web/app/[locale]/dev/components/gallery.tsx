"use client";

import { Bell, Mail } from "lucide-react";
import { useState } from "react";

import { AuditDrawer } from "@/components/common/audit-drawer";
import { DataTable } from "@/components/common/data-table";
import { FileDropzone } from "@/components/common/file-dropzone";
import { KpiCard } from "@/components/common/kpi-card";
import { Timeline } from "@/components/common/timeline";
import { LanguageSwitcher } from "@/components/shell/language-switcher";
import { AiBadge } from "@/components/status/ai-badge";
import { ConfidenceRing } from "@/components/status/confidence-ring";
import { IconBadge } from "@/components/status/icon-badge";
import type { AppStatus } from "@/components/status/status-chip";
import { StatusChip } from "@/components/status/status-chip";
import { SlaBadge } from "@/components/status/sla-badge";
import { SlaPill } from "@/components/status/sla-pill";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";

const ALL_STATUSES: AppStatus[] = [
  "DRAFT",
  "SUBMITTED",
  "IN_PROCESS",
  "DECISION_RECORDED",
  "APPROVED",
  "APPROVED_WITH_CONDITIONS",
  "REJECTED",
  "WITHDRAWN",
  "PENDING",
  "ACTIVE",
  "COMPLETED",
  "RETURNED",
  "REFERRED",
  "SKIPPED",
];

const now = new Date();
const inDays = (n: number) => new Date(now.getTime() + n * 86400000).toISOString();

const SAMPLE_TIMELINE = [
  { id: "1", actor: "Scrutiny Officer", action: "cleared the stage", at: inDays(-2) },
  { id: "2", actor: "Institution", action: "resubmitted documents", at: inDays(-5) },
  { id: "3", actor: "System", action: "routed the application", at: inDays(-7) },
];

const SAMPLE_ROWS = [
  { id: "APP-2026-0451", institution: "Govt. Engineering College", stage: "SCRUTINY" },
  { id: "APP-2026-0452", institution: "City Polytechnic", stage: "EVC" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </section>
  );
}

function Panel({ theme }: { theme: "light" | "dark" }) {
  const [auditOpen, setAuditOpen] = useState(false);

  return (
    <div data-theme={theme} className="flex-1 space-y-8 rounded-2xl border border-border bg-bg p-6 text-text">
      <h1 className="text-lg font-semibold capitalize">{theme} theme</h1>

      <Section title="Buttons">
        <Button variant="solid">Clear Stage &amp; Forward</Button>
        <Button variant="outline">Refer to Senior</Button>
        <Button variant="danger">Return for Deficiency</Button>
        <Button variant="ai">AI Assistant Chat</Button>
        <Button variant="ghost">Cancel</Button>
      </Section>

      <Section title="Status chip">
        {ALL_STATUSES.map((s) => (
          <StatusChip key={s} status={s} />
        ))}
      </Section>

      <Section title="SLA badge / pill">
        <SlaBadge dueAt={inDays(12)} now={now} />
        <SlaBadge dueAt={inDays(2)} now={now} />
        <SlaBadge dueAt={inDays(-3)} now={now} />
        <SlaPill dueAt={inDays(12)} now={now} />
        <SlaPill dueAt={inDays(2)} now={now} />
        <SlaPill dueAt={inDays(-3)} now={now} />
      </Section>

      <Section title="Confidence ring">
        <ConfidenceRing value={98} />
        <ConfidenceRing value={78} />
        <ConfidenceRing value={55} />
      </Section>

      <Section title="AI badge / icon badge">
        <AiBadge />
        <IconBadge icon={Mail} count={3} label="Mail" className="bg-surface-2 text-text hover:bg-surface" />
        <IconBadge icon={Bell} count={0} label="Notifications" className="bg-surface-2 text-text hover:bg-surface" />
      </Section>

      <Section title="KPI cards">
        <KpiCard label="Active Applications" value={128} />
        <KpiCard label="Overdue" value={6} tone="danger" />
        <KpiCard label="Cleared this week" value={41} tone="success" />
      </Section>

      <Section title="Theme toggle / language switcher">
        <ThemeToggle />
        <LanguageSwitcher />
      </Section>

      <Section title="Timeline">
        <div className="w-full max-w-md rounded-xl border border-border bg-surface p-4">
          <Timeline entries={SAMPLE_TIMELINE} />
        </div>
      </Section>

      <Section title="Data table">
        <DataTable
          columns={[
            { key: "id", header: "App ID", render: (r) => r.id },
            { key: "institution", header: "Institution", render: (r) => r.institution },
            { key: "stage", header: "Stage", render: (r) => r.stage },
          ]}
          rows={SAMPLE_ROWS}
          rowKey={(r) => r.id}
          className="w-full"
        />
      </Section>

      <Section title="File dropzone">
        <FileDropzone onFiles={() => {}} status={{ label: "Extracting fields…", progress: 60 }} className="w-full" />
      </Section>

      <Section title="Audit drawer">
        <Button variant="outline" onClick={() => setAuditOpen(true)}>
          Open audit drawer
        </Button>
        <AuditDrawer open={auditOpen} onOpenChange={setAuditOpen} title="Audit — APP-2026-0451" entries={SAMPLE_TIMELINE} />
      </Section>
    </div>
  );
}

export function ComponentGallery() {
  return (
    <main className="min-h-screen bg-bg p-6">
      <h1 className="mb-6 text-2xl font-semibold text-text">Component gallery (dev only)</h1>
      <div className="flex flex-col gap-6 lg:flex-row">
        <Panel theme="light" />
        <Panel theme="dark" />
      </div>
    </main>
  );
}

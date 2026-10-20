import { getTranslations } from "next-intl/server";

import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { SlaBadge } from "@/components/status/sla-badge";
import { Link } from "@/i18n/navigation";
import type { StageInstanceOut } from "@/lib/api";
import { apiServerGet } from "@/lib/api-server";

export default async function OfficerQueuePage() {
  const queue = (await apiServerGet<StageInstanceOut[]>("/api/v1/queue")) ?? [];
  const t = await getTranslations("queue");

  const columns: DataTableColumn<StageInstanceOut>[] = [
    { key: "appNo", header: t("table.appNo"), render: (s) => s.app_no ?? "—" },
    { key: "institution", header: t("table.institution"), render: (s) => s.institution_name },
    { key: "stage", header: t("table.stage"), render: (s) => s.stage_key },
    {
      key: "sla",
      header: t("table.sla"),
      render: (s) => (s.deadline ? <SlaBadge dueAt={s.deadline.due_at} /> : "—"),
    },
    { key: "aiFlags", header: t("table.aiFlags"), render: (s) => s.ai_flag_count },
    {
      key: "actions",
      header: "",
      className: "text-right",
      render: (s) => (
        <Link href={`/officer/queue/${s.id}`} className="font-medium text-primary hover:underline">
          {t("openAction")}
        </Link>
      ),
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs items={[{ label: t("title") }]} />
      <div className="p-4 md:p-6">
        <DataTable columns={columns} rows={queue} rowKey={(s) => s.id} emptyLabel={t("empty")} />
      </div>
    </div>
  );
}

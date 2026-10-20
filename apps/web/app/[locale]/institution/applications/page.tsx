import { getTranslations } from "next-intl/server";

import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { StatusChip } from "@/components/status/status-chip";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import type { ApplicationOut } from "@/lib/api";
import { apiServerGet } from "@/lib/api-server";

export default async function InstitutionApplicationsPage() {
  const applications = (await apiServerGet<ApplicationOut[]>("/api/v1/applications")) ?? [];
  const t = await getTranslations("applications");
  const tType = await getTranslations("applicationType");

  const columns: DataTableColumn<ApplicationOut>[] = [
    { key: "appNo", header: t("table.appNo"), render: (a) => a.app_no ?? t("notSubmitted") },
    { key: "type", header: t("table.type"), render: (a) => tType(a.application_type) },
    { key: "status", header: t("table.status"), render: (a) => <StatusChip status={a.status} /> },
    { key: "stage", header: t("table.stage"), render: (a) => a.current_stage_key ?? "—" },
    {
      key: "submitted",
      header: t("table.submitted"),
      render: (a) => (a.submitted_at ? new Date(a.submitted_at).toLocaleDateString() : "—"),
    },
    {
      key: "actions",
      header: "",
      className: "text-right",
      render: (a) => (
        <Link href={`/institution/applications/${a.id}`} className="font-medium text-primary hover:underline">
          {t("viewAction")}
        </Link>
      ),
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <Breadcrumbs
        items={[{ label: t("title") }]}
        trailing={
          <Link href="/institution/applications/new">
            <Button size="sm">{t("new")}</Button>
          </Link>
        }
      />
      <div className="p-4 md:p-6">
        <DataTable columns={columns} rows={applications} rowKey={(a) => a.id} emptyLabel={t("empty")} />
      </div>
    </div>
  );
}

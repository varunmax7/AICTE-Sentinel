import { ApplicationDetail } from "@/components/applications/application-detail";
import type { AiReportOut, ApplicationOut, DocumentOut, StageInstanceOut, TimelineEntryOut } from "@/lib/api";
import { apiServerGet } from "@/lib/api-server";

export default async function InstitutionApplicationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [application, stages, timeline, documents, aiReport] = await Promise.all([
    apiServerGet<ApplicationOut>(`/api/v1/applications/${id}`),
    apiServerGet<StageInstanceOut[]>(`/api/v1/applications/${id}/stages`),
    apiServerGet<TimelineEntryOut[]>(`/api/v1/applications/${id}/timeline`),
    apiServerGet<DocumentOut[]>(`/api/v1/applications/${id}/documents`),
    apiServerGet<AiReportOut>(`/api/v1/applications/${id}/ai-report`),
  ]);
  if (!application) return null;

  return (
    <ApplicationDetail
      application={application}
      stages={stages ?? []}
      timeline={timeline ?? []}
      documents={documents ?? []}
      aiReport={aiReport}
    />
  );
}

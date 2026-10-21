import { StageDetail } from "@/components/applications/stage-detail";
import type { AiReportOut, ApplicationOut, DocumentOut, StageInstanceOut } from "@/lib/api";
import { apiServerGet } from "@/lib/api-server";

export default async function OfficerStageDetailPage({
  params,
}: {
  params: Promise<{ stageId: string }>;
}) {
  const { stageId } = await params;
  const stage = await apiServerGet<StageInstanceOut>(`/api/v1/stages/${stageId}`);
  if (!stage) return null;

  const [application, applicationStages, documents, aiReport] = await Promise.all([
    apiServerGet<ApplicationOut>(`/api/v1/applications/${stage.application_id}`),
    apiServerGet<StageInstanceOut[]>(`/api/v1/applications/${stage.application_id}/stages`),
    apiServerGet<DocumentOut[]>(`/api/v1/applications/${stage.application_id}/documents`),
    apiServerGet<AiReportOut>(`/api/v1/applications/${stage.application_id}/ai-report`),
  ]);

  return (
    <StageDetail
      stage={stage}
      application={application}
      applicationStages={applicationStages ?? []}
      documents={documents ?? []}
      aiReport={aiReport}
    />
  );
}

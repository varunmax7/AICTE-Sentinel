import { ApplicationDetail } from "@/components/applications/application-detail";
import type { ApplicationOut, StageInstanceOut, TimelineEntryOut } from "@/lib/api";
import { apiServerGet } from "@/lib/api-server";

export default async function InstitutionApplicationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [application, stages, timeline] = await Promise.all([
    apiServerGet<ApplicationOut>(`/api/v1/applications/${id}`),
    apiServerGet<StageInstanceOut[]>(`/api/v1/applications/${id}/stages`),
    apiServerGet<TimelineEntryOut[]>(`/api/v1/applications/${id}/timeline`),
  ]);
  if (!application) return null;

  return <ApplicationDetail application={application} stages={stages ?? []} timeline={timeline ?? []} />;
}

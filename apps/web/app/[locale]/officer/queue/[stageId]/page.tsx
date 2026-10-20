import { StageDetail } from "@/components/applications/stage-detail";
import type { StageInstanceOut } from "@/lib/api";
import { apiServerGet } from "@/lib/api-server";

export default async function OfficerStageDetailPage({
  params,
}: {
  params: Promise<{ stageId: string }>;
}) {
  const { stageId } = await params;
  const stage = await apiServerGet<StageInstanceOut>(`/api/v1/stages/${stageId}`);
  if (!stage) return null;

  return <StageDetail stage={stage} />;
}

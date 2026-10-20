import { ApplicationWizard } from "@/components/applications/application-wizard";
import type { ApplicationTypeOut, InstitutionOut } from "@/lib/api";
import { apiServerGet, getServerMe } from "@/lib/api-server";

export default async function NewApplicationPage() {
  const me = await getServerMe();
  if (!me || !me.institution_id) return null;

  const [applicationTypes, institution] = await Promise.all([
    apiServerGet<ApplicationTypeOut[]>("/api/v1/application-types"),
    apiServerGet<InstitutionOut>(`/api/v1/institutions/${me.institution_id}`),
  ]);
  if (!applicationTypes || !institution) return null;

  return <ApplicationWizard applicationTypes={applicationTypes} institution={institution} />;
}

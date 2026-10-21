import { useTranslations } from "next-intl";

import type { ApplicationOut, StageInstanceOut } from "@/lib/api";

import { StageStepper } from "./stage-stepper";

/** Left column of the Case Review Workspace (IMPLEMENTATION.md §7.1, §15.3). */
export function CaseFilePanel({
  stage,
  application,
  stages,
}: {
  stage: StageInstanceOut;
  application: ApplicationOut | null;
  stages: StageInstanceOut[];
}) {
  const t = useTranslations("caseReview.caseFile");
  const tType = useTranslations("applicationType");

  return (
    <div className="h-full overflow-y-auto border-r border-border p-4">
      <h2 className="text-base font-semibold text-text">{stage.institution_name}</h2>
      <p className="font-mono text-xs text-muted">{stage.app_no}</p>
      {application && <p className="mt-0.5 text-xs text-muted">{tType(application.application_type)}</p>}

      <div className="mt-5">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">{t("stages")}</p>
        <StageStepper stages={stages} orientation="vertical" />
      </div>

      {application && (
        <div className="mt-5 space-y-1.5 border-t border-border pt-4 text-xs">
          <p className="mb-1 font-medium uppercase tracking-wide text-muted">{t("keyFacts")}</p>
          <div className="flex justify-between">
            <span className="text-muted">{t("academicYear")}</span>
            <span className="text-text">{application.academic_year}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">{t("courses")}</span>
            <span className="text-text">{application.courses.length}</span>
          </div>
          {application.payload.land_area_acres != null && (
            <div className="flex justify-between">
              <span className="text-muted">{t("landArea")}</span>
              <span className="text-text">{String(application.payload.land_area_acres)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { AuditDrawer } from "@/components/common/audit-drawer";
import { Timeline, type TimelineEntry } from "@/components/common/timeline";
import { AiCheckList } from "@/components/documents/ai-panel";
import { StatusChip } from "@/components/status/status-chip";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  type AiReportOut,
  type ApplicationOut,
  type DeficiencyOut,
  type DocumentOut,
  type StageInstanceOut,
  type TimelineEntryOut,
  documentAssetUrl,
  getStageDeficiencies,
  resubmitApplication,
  withdrawApplication,
} from "@/lib/api";

import { StageStepper } from "./stage-stepper";

const TABS = ["overview", "documents", "deficiencies", "evc", "timeline", "communications"] as const;
type Tab = (typeof TABS)[number];

const REASON_CODE_KEY: Record<string, string> = {
  MISSING_DOCUMENT: "missingDocument",
  FIRE_NOC_EXPIRED: "fireNocExpired",
  LAND_AREA_SHORTFALL: "landAreaShortfall",
  INVALID_SIGNATURE: "invalidSignature",
  INCOMPLETE_FACULTY_DATA: "incompleteFacultyData",
  OTHER: "other",
};

const DOCUMENT_TYPE_KEY: Record<string, string> = {
  LEASE_DEED: "leaseDeed",
  BUILDING_PLAN_APPROVAL: "buildingPlanApproval",
  FIRE_NOC: "fireNoc",
  AFFIDAVIT: "affidavit",
  FACULTY_LIST: "facultyList",
};

function toTimelineEntries(entries: TimelineEntryOut[]): TimelineEntry[] {
  return entries.map((e) => ({ id: e.id, actor: e.actor, action: e.action, at: e.at, channel: e.channel ?? undefined }));
}

export function ApplicationDetail({
  application: initialApplication,
  stages,
  timeline,
  documents,
  aiReport,
}: {
  application: ApplicationOut;
  stages: StageInstanceOut[];
  timeline: TimelineEntryOut[];
  documents: DocumentOut[];
  aiReport: AiReportOut | null;
}) {
  const t = useTranslations("applications.detail");
  const tType = useTranslations("applicationType");
  const tDeficiency = useTranslations("deficiency");
  const tDocType = useTranslations("documentType");

  const [application, setApplication] = useState(initialApplication);
  const [tab, setTab] = useState<Tab>("overview");
  const [auditOpen, setAuditOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const returnedStage = stages.find((s) => s.status === "RETURNED");
  const [deficiencies, setDeficiencies] = useState<DeficiencyOut[]>([]);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tab === "deficiencies" && returnedStage) {
      getStageDeficiencies(returnedStage.id)
        .then(setDeficiencies)
        .catch(() => setDeficiencies([]));
    }
  }, [tab, returnedStage]);

  async function handleRespond() {
    if (!returnedStage) return;
    setLoading(true);
    setError(null);
    try {
      const payload = deficiencies
        .filter((d) => d.status === "OPEN" && responses[d.id])
        .map((d) => ({ deficiency_id: d.id, response_text: responses[d.id] }));
      const updated = await resubmitApplication(application.id, payload);
      setApplication(updated);
      setResponses({});
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "GENERIC");
    } finally {
      setLoading(false);
    }
  }

  async function handleWithdraw() {
    if (!window.confirm(t("withdrawConfirm"))) return;
    setLoading(true);
    try {
      const updated = await withdrawApplication(application.id);
      setApplication(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "GENERIC");
    } finally {
      setLoading(false);
    }
  }

  const timelineEntries = toTimelineEntries(timeline);
  const canWithdraw = application.status === "SUBMITTED" || application.status === "IN_PROCESS";

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3 md:px-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-text">{application.app_no ?? tType(application.application_type)}</h1>
            <p className="text-sm text-muted">{tType(application.application_type)}</p>
          </div>
          <div className="flex items-center gap-2">
            <StatusChip status={application.status} />
            {canWithdraw && (
              <Button variant="outline" size="sm" onClick={handleWithdraw} disabled={loading}>
                {t("withdraw")}
              </Button>
            )}
            <AuditDrawer
              open={auditOpen}
              onOpenChange={setAuditOpen}
              title={t("auditTrail")}
              entries={timelineEntries}
              trigger={
                <Button variant="outline" size="sm">
                  {t("auditTrail")}
                </Button>
              }
            />
          </div>
        </div>
        {stages.length > 0 && (
          <div className="mt-4">
            <StageStepper stages={stages} />
          </div>
        )}
        <nav className="mt-4 flex gap-4 border-b border-border text-sm">
          {TABS.map((tb) => (
            <button
              key={tb}
              onClick={() => setTab(tb)}
              className={`-mb-px border-b-2 px-1 pb-2 ${
                tab === tb ? "border-primary font-medium text-primary" : "border-transparent text-muted hover:text-text"
              }`}
            >
              {t(`tabs.${tb}`)}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {error && <p className="mb-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}

        {tab === "overview" && (
          <dl className="max-w-md space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">{t("currentStage")}</dt>
              <dd className="text-text">{application.current_stage_key ?? "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">{tType(application.application_type)}</dt>
              <dd className="text-text">{application.academic_year}</dd>
            </div>
          </dl>
        )}

        {tab === "documents" && (
          <div className="max-w-2xl space-y-4">
            {documents.length === 0 ? (
              <p className="text-sm text-muted">{t("documentsPlaceholder")}</p>
            ) : (
              <ul className="space-y-2">
                {documents.map((doc) => (
                  <li key={doc.id} className="flex items-center gap-3 rounded-lg border border-border p-3">
                    {doc.preview_url && (
                      // eslint-disable-next-line @next/next/no-img-element -- backend-streamed, not a Next static asset
                      <img
                        src={documentAssetUrl(doc.preview_url)}
                        alt=""
                        className="size-12 shrink-0 rounded border border-border object-cover"
                      />
                    )}
                    <div className="flex-1">
                      <p className="text-sm font-medium text-text">
                        {tDocType(DOCUMENT_TYPE_KEY[doc.document_type] ?? doc.document_type)}
                      </p>
                      {doc.extraction && (
                        <p className="text-xs text-muted">
                          {t("documentConfidence", { confidence: Math.round(doc.extraction.confidence) })}
                        </p>
                      )}
                    </div>
                    <StatusChip
                      status={doc.verified_status === "VERIFIED" ? "COMPLETED" : doc.verified_status === "REJECTED" ? "REJECTED" : "PENDING"}
                    />
                    <a
                      href={documentAssetUrl(doc.download_url)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      {t("viewDocument")}
                    </a>
                  </li>
                ))}
              </ul>
            )}
            {aiReport && aiReport.checks.length > 0 && (
              <div>
                <h2 className="mb-2 text-sm font-semibold text-text">{t("aiPreScrutiny")}</h2>
                <AiCheckList checks={aiReport.checks} />
              </div>
            )}
          </div>
        )}

        {tab === "deficiencies" && (
          <div className="max-w-md space-y-4">
            {!returnedStage ? (
              <p className="text-sm text-muted">{t("noDeficiencies")}</p>
            ) : (
              <>
                <h2 className="text-sm font-semibold text-text">{t("respondTitle")}</h2>
                {deficiencies.map((d) => (
                  <div key={d.id} className="rounded-lg border border-border p-3">
                    <p className="text-sm font-medium text-text">
                      {d.reason_code && REASON_CODE_KEY[d.reason_code]
                        ? tDeficiency(REASON_CODE_KEY[d.reason_code] as never)
                        : d.custom_text}
                    </p>
                    {d.custom_text && d.reason_code && <p className="text-xs text-muted">{d.custom_text}</p>}
                    {d.status === "OPEN" ? (
                      <textarea
                        value={responses[d.id] ?? ""}
                        onChange={(e) => setResponses((prev) => ({ ...prev, [d.id]: e.target.value }))}
                        placeholder={t("responseLabel")}
                        className="mt-2 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text"
                      />
                    ) : (
                      <p className="mt-2 text-xs text-success">{d.response_text}</p>
                    )}
                  </div>
                ))}
                {deficiencies.some((d) => d.status === "OPEN") && (
                  <Button onClick={handleRespond} disabled={loading}>
                    {t("submitResponse")}
                  </Button>
                )}
              </>
            )}
          </div>
        )}

        {tab === "evc" && <p className="text-sm text-muted">{t("evcPlaceholder")}</p>}

        {tab === "timeline" && <Timeline entries={timelineEntries} />}

        {tab === "communications" && <p className="text-sm text-muted">{t("communicationsPlaceholder")}</p>}
      </div>
    </div>
  );
}

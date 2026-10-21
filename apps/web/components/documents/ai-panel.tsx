"use client";

import { useTranslations } from "next-intl";

import { ConfidenceRing } from "@/components/status/confidence-ring";
import type { AiCheckOut, AiReportOut } from "@/lib/api";

import { CheckCard } from "./check-card";

const TITLE_KEY: Record<string, string> = {
  LAND_AREA_NORMS: "landAreaNorms",
  STAMP_DUTY_SANITY: "stampDuty",
  DOCUMENT_VALIDITY: "documentValidity",
  INFRASTRUCTURE_VERIFICATION: "infrastructure",
  DUPLICATE_FACULTY: "duplicateFaculty",
};

function CheckBody({ check }: { check: AiCheckOut }) {
  const t = useTranslations("aiCheck");
  const p = check.params;

  switch (check.check_key) {
    case "LAND_AREA_NORMS":
      return "extracted" in p ? (
        <>{t("landAreaNorms.result", { extracted: p.extracted as number, required: p.required as number })}</>
      ) : (
        <>{t("landAreaNorms.noData")}</>
      );
    case "STAMP_DUTY_SANITY":
      return "amount" in p ? (
        <>{t("stampDuty.result", { amount: p.amount as number, expectedMin: p.expectedMin as number })}</>
      ) : (
        <>{t("stampDuty.noData")}</>
      );
    case "DOCUMENT_VALIDITY":
      return "expiry" in p ? (
        <>{t("documentValidity.result", { expiry: p.expiry as string, requiredUntil: p.requiredUntil as string })}</>
      ) : (
        <>{t("documentValidity.noData")}</>
      );
    case "INFRASTRUCTURE_VERIFICATION": {
      const missing = (p.missing as string[]) ?? [];
      return (
        <>
          {t("infrastructure.result", { completePct: p.completePct as number })}
          {missing.length > 0 && <> — {t("infrastructure.missing", { items: missing.join(", ") })}</>}
        </>
      );
    }
    case "DUPLICATE_FACULTY":
      return <>{t("duplicateFaculty.result")}</>;
    default:
      return null;
  }
}

/** Reused by the application wizard's precheck step, without the confidence ring. */
export function AiCheckList({ checks }: { checks: AiCheckOut[] }) {
  const t = useTranslations("aiCheck");

  if (checks.length === 0) {
    return <p className="text-sm text-muted">{t("noChecksYet")}</p>;
  }

  return (
    <div className="space-y-2">
      {checks.map((check) => (
        <CheckCard
          key={check.check_key}
          title={t(`titles.${TITLE_KEY[check.check_key] ?? check.check_key}`)}
          status={check.status}
        >
          <CheckBody check={check} />
        </CheckCard>
      ))}
    </div>
  );
}

export function AiPanel({ report }: { report: AiReportOut | null }) {
  const t = useTranslations("aiCheck");

  if (!report) {
    return <p className="p-4 text-sm text-muted">{t("noReport")}</p>;
  }

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div className="flex flex-col items-center gap-2 rounded-xl border border-border bg-surface p-4">
        <ConfidenceRing value={report.confidence} size={72} />
        <p className="text-xs text-muted">{t("preScrutinyConfidence")}</p>
      </div>
      <AiCheckList checks={report.checks} />
    </div>
  );
}

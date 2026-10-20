"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { ActionBar } from "@/components/shell/action-bar";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import {
  ApiError,
  type ApplicationCourse,
  type ApplicationOut,
  type ApplicationType,
  type ApplicationTypeOut,
  type InstitutionOut,
  createApplication,
  precheckApplication,
  sendSubmitOtp,
  submitApplication,
  updateApplication,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const STEPS = [
  "type",
  "institution",
  "courses",
  "landBuilding",
  "faculty",
  "documents",
  "precheck",
  "review",
] as const;

type Step = (typeof STEPS)[number];

const COURSE_LEVELS = ["UG", "PG", "DIPLOMA"];

export function ApplicationWizard({
  applicationTypes,
  institution,
}: {
  applicationTypes: ApplicationTypeOut[];
  institution: InstitutionOut;
}) {
  const t = useTranslations("applications.wizard");
  const tType = useTranslations("applicationType");

  const [stepIndex, setStepIndex] = useState(0);
  const step: Step = STEPS[stepIndex];

  const [applicationType, setApplicationType] = useState<ApplicationType>(
    applicationTypes[0]?.code ?? "EXTENSION_OF_APPROVAL"
  );
  const [academicYear, setAcademicYear] = useState("2026-27");
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [requiredDocs, setRequiredDocs] = useState<string[]>([]);
  const [courses, setCourses] = useState<ApplicationCourse[]>([]);
  const [payload, setPayload] = useState<Record<string, unknown>>({});
  const [documentsChecked, setDocumentsChecked] = useState<Record<string, boolean>>({});
  const [precheckRan, setPrecheckRan] = useState(false);

  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [submitted, setSubmitted] = useState<ApplicationOut | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function errorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const key = `errors.${err.code}` as Parameters<typeof t>[0];
      if (t.has(key)) return t(key);
    }
    return t("errors.GENERIC");
  }

  async function goNext(persist?: () => Promise<void>) {
    setError(null);
    setLoading(true);
    try {
      if (persist) await persist();
      setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function goBack() {
    setError(null);
    setStepIndex((i) => Math.max(i - 1, 0));
  }

  async function handleStartDraft() {
    setError(null);
    setLoading(true);
    try {
      const created = await createApplication({ application_type: applicationType, academic_year: academicYear });
      setApplicationId(created.id);
      setRequiredDocs(applicationTypes.find((at) => at.code === applicationType)?.required_document_types ?? []);
      setStepIndex(1);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function updateCourse(index: number, patch: Partial<ApplicationCourse>) {
    setCourses((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  }

  async function handleRunPrecheck() {
    if (!applicationId) return;
    setLoading(true);
    try {
      await precheckApplication(applicationId);
      setPrecheckRan(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleSendOtp() {
    if (!applicationId) return;
    setError(null);
    setLoading(true);
    try {
      await sendSubmitOtp(applicationId);
      setOtpSent(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (!applicationId) return;
    setError(null);
    setLoading(true);
    try {
      const result = await submitApplication(applicationId, otpCode);
      setSubmitted(result);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="mx-auto max-w-xl p-6 text-center">
        <p className="rounded-xl border border-success-soft bg-success-soft p-4 text-sm font-medium text-success">
          {t("review.success", { appNo: submitted.app_no ?? "" })}
        </p>
        <Link href={`/institution/applications/${submitted.id}`} className="mt-4 inline-block">
          <Button>{t("review.title")}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3 md:px-6">
        <h1 className="text-lg font-semibold text-text">{t("title")}</h1>
        <ol className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {STEPS.map((s, i) => (
            <li
              key={s}
              className={cn(
                "flex items-center gap-1.5",
                i === stepIndex ? "font-semibold text-primary" : i < stepIndex ? "text-success" : "text-muted"
              )}
            >
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full border text-[10px]",
                  i === stepIndex
                    ? "border-primary text-primary"
                    : i < stepIndex
                      ? "border-success bg-success-soft text-success"
                      : "border-border"
                )}
              >
                {i + 1}
              </span>
              {t(`steps.${s}`)}
            </li>
          ))}
        </ol>
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {error && <p className="mb-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}

        {step === "type" && (
          <div className="max-w-md space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">{t("typeLabel")}</label>
              <select
                value={applicationType}
                onChange={(e) => setApplicationType(e.target.value as ApplicationType)}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
              >
                {applicationTypes.map((at) => (
                  <option key={at.code} value={at.code}>
                    {tType(at.code)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">{t("academicYearLabel")}</label>
              <input
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
              />
            </div>
            <Button onClick={handleStartDraft} disabled={loading}>
              {t("startDraft")}
            </Button>
          </div>
        )}

        {step === "institution" && (
          <div className="max-w-md space-y-3">
            <p className="text-sm text-muted">{t("institutionNote")}</p>
            <div className="rounded-xl border border-border bg-surface p-4 text-sm">
              <p className="font-medium text-text">{institution.name}</p>
              <p className="text-muted">{institution.aicte_id}</p>
              <p className="text-muted">
                {institution.city} · {institution.type}
              </p>
            </div>
          </div>
        )}

        {step === "courses" && (
          <div className="max-w-2xl space-y-3">
            {courses.length === 0 && <p className="text-sm text-muted">{t("courses.empty")}</p>}
            {courses.map((course, i) => (
              <div key={i} className="grid grid-cols-2 gap-2 rounded-lg border border-border p-3 sm:grid-cols-5">
                <input
                  value={course.course_name}
                  onChange={(e) => updateCourse(i, { course_name: e.target.value })}
                  placeholder={t("courses.nameLabel")}
                  className="col-span-2 rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text sm:col-span-2"
                />
                <select
                  value={course.level}
                  onChange={(e) => updateCourse(i, { level: e.target.value })}
                  className="rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text"
                >
                  {COURSE_LEVELS.map((lvl) => (
                    <option key={lvl} value={lvl}>
                      {lvl}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  value={course.existing_intake}
                  onChange={(e) => updateCourse(i, { existing_intake: Number(e.target.value) })}
                  placeholder={t("courses.existingIntakeLabel")}
                  className="rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text"
                />
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={course.proposed_intake}
                    onChange={(e) => updateCourse(i, { proposed_intake: Number(e.target.value) })}
                    placeholder={t("courses.proposedIntakeLabel")}
                    className="w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text"
                  />
                  <button
                    type="button"
                    onClick={() => setCourses((prev) => prev.filter((_, idx) => idx !== i))}
                    className="shrink-0 text-xs text-danger hover:underline"
                  >
                    {t("courses.remove")}
                  </button>
                </div>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setCourses((prev) => [
                  ...prev,
                  { course_name: "", level: "UG", existing_intake: 0, proposed_intake: 0 },
                ])
              }
            >
              {t("courses.add")}
            </Button>
          </div>
        )}

        {step === "landBuilding" && (
          <div className="max-w-md space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">{t("landBuilding.landAreaLabel")}</label>
              <input
                type="number"
                value={(payload.land_area_acres as string) ?? ""}
                onChange={(e) => setPayload((p) => ({ ...p, land_area_acres: e.target.value }))}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">
                {t("landBuilding.builtUpAreaLabel")}
              </label>
              <input
                type="number"
                value={(payload.built_up_area_sqft as string) ?? ""}
                onChange={(e) => setPayload((p) => ({ ...p, built_up_area_sqft: e.target.value }))}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
              />
            </div>
          </div>
        )}

        {step === "faculty" && (
          <div className="max-w-md space-y-3">
            <p className="rounded-lg bg-ai-soft px-3 py-2 text-sm text-ai">{t("faculty.importNote")}</p>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">{t("faculty.importLabel")}</label>
              <input type="file" accept=".xlsx" disabled className="w-full text-sm text-muted" />
            </div>
          </div>
        )}

        {step === "documents" && (
          <div className="max-w-md space-y-3">
            <p className="text-sm text-muted">{t("documents.checklistNote")}</p>
            {requiredDocs.length === 0 ? (
              <p className="text-sm text-muted">{t("documents.empty")}</p>
            ) : (
              <ul className="space-y-2">
                {requiredDocs.map((doc) => (
                  <li key={doc} className="flex items-center gap-2 rounded-lg border border-border p-2.5 text-sm">
                    <input
                      type="checkbox"
                      checked={documentsChecked[doc] ?? false}
                      onChange={(e) => setDocumentsChecked((prev) => ({ ...prev, [doc]: e.target.checked }))}
                    />
                    <span className="text-text">{doc}</span>
                    <span className="ml-auto text-xs text-muted">{t("documents.haveIt")}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {step === "precheck" && (
          <div className="max-w-md space-y-3">
            <h2 className="text-sm font-semibold text-text">{t("precheck.pendingTitle")}</h2>
            <p className="rounded-lg bg-ai-soft px-3 py-2 text-sm text-ai">{t("precheck.pendingNote")}</p>
            <Button variant="outline" size="sm" onClick={handleRunPrecheck} disabled={loading || precheckRan}>
              {t("precheck.run")}
            </Button>
          </div>
        )}

        {step === "review" && (
          <div className="max-w-md space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-text">{t("review.summary")}</h2>
              <dl className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted">{t("typeLabel")}</dt>
                  <dd className="text-text">{tType(applicationType)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">{t("academicYearLabel")}</dt>
                  <dd className="text-text">{academicYear}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">{t("steps.courses")}</dt>
                  <dd className="text-text">{courses.length}</dd>
                </div>
              </dl>
            </div>

            {!otpSent ? (
              <div>
                <p className="mb-2 text-sm text-muted">{t("review.otpNote")}</p>
                <Button onClick={handleSendOtp} disabled={loading}>
                  {t("review.sendOtp")}
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-muted">{t("review.otpLabel")}</label>
                  <input
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    maxLength={6}
                    inputMode="numeric"
                    className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-center text-lg tracking-widest text-text"
                  />
                </div>
                <Button onClick={handleSubmit} disabled={loading || otpCode.length === 0}>
                  {t("review.submit")}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <ActionBar>
        <Button variant="outline" onClick={goBack} disabled={stepIndex === 0 || loading}>
          {t("back")}
        </Button>
        {step !== "type" && step !== "review" && (
          <Button
            onClick={() =>
              goNext(async () => {
                if (!applicationId) return;
                if (step === "courses") await updateApplication(applicationId, { courses });
                if (step === "landBuilding") await updateApplication(applicationId, { payload });
                if (step === "documents")
                  await updateApplication(applicationId, {
                    payload: { ...payload, documents_checklist: documentsChecked },
                  });
              })
            }
            disabled={loading}
          >
            {t("next")}
          </Button>
        )}
      </ActionBar>
    </div>
  );
}

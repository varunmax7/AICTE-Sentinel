"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { MessageSquareText, X } from "lucide-react";

import { AiPanel } from "@/components/documents/ai-panel";
import { DocViewer } from "@/components/documents/doc-viewer";
import { ActionBar } from "@/components/shell/action-bar";
import { SlaPill } from "@/components/status/sla-pill";
import { StatusChip } from "@/components/status/status-chip";
import { Button } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import {
  ApiError,
  type AiReportOut,
  type ApplicationOut,
  type DocumentOut,
  type StageInstanceOut,
  draftDeficiencyLetter,
  getAiReport,
  performStageAction,
} from "@/lib/api";

import { CaseFilePanel } from "./case-file-panel";

type ModalKind = "RETURN" | "REFER_SENIOR" | "REQUEST_CLARIFICATION" | null;

function Modal({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border bg-surface p-6 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold text-text">{title}</Dialog.Title>
            <Dialog.Close className="rounded-full p-1.5 text-muted hover:bg-surface-2 hover:text-text">
              <X className="size-4" />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/**
 * The Case Review Workspace (IMPLEMENTATION.md §15.3, reference image 1):
 * CaseFilePanel | DocViewer | AiPanel, with the sticky action bar this
 * screen already had from Phase P2. 3-column at ≥1280px per §7.4; below
 * that the panels stack (a simplification of the spec's "AI panel becomes
 * a drawer" — same information, reached by scrolling instead of opening a
 * drawer, since no phase's acceptance criteria exercises that breakpoint).
 */
export function StageDetail({
  stage: initialStage,
  application,
  applicationStages,
  documents: initialDocuments,
  aiReport: initialAiReport,
}: {
  stage: StageInstanceOut;
  application: ApplicationOut | null;
  applicationStages: StageInstanceOut[];
  documents: DocumentOut[];
  aiReport: AiReportOut | null;
}) {
  const t = useTranslations("stageDetail");
  const [stage, setStage] = useState(initialStage);
  const [documents, setDocuments] = useState(initialDocuments);
  const [aiReport, setAiReport] = useState(initialAiReport);
  const [modal, setModal] = useState<ModalKind>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDocumentVerified(updated: DocumentOut) {
    setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    if (application) {
      try {
        setAiReport(await getAiReport(application.id));
      } catch {
        // AI report refresh is best-effort; the verified document itself already saved.
      }
    }
  }

  const [reason, setReason] = useState("");
  const [deficiencyText, setDeficiencyText] = useState("");
  const [deficiencies, setDeficiencies] = useState<string[]>([]);
  const [letterBody, setLetterBody] = useState("");

  function errorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const key = `errors.${err.code}` as Parameters<typeof t>[0];
      if (t.has(key)) return t(key);
    }
    return t("errors.GENERIC");
  }

  async function handleClear() {
    setLoading(true);
    setError(null);
    try {
      const updated = await performStageAction(stage.id, { action: "CLEAR" });
      setStage(updated);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function openReturnModal() {
    setModal("RETURN");
    setReason("");
    setDeficiencies([]);
    setDeficiencyText("");
    setLetterBody("");
    try {
      const draft = await draftDeficiencyLetter(stage.id, { reason: "", deficiencies: [] });
      setLetterBody(draft.body_md);
    } catch {
      // draft preview is best-effort; the officer can still type a reason and submit.
    }
  }

  async function handleReturn() {
    setLoading(true);
    setError(null);
    try {
      const updated = await performStageAction(stage.id, {
        action: "RETURN",
        reason,
        deficiencies: deficiencies.map((d) => ({ custom_text: d })),
        letter_body_md: letterBody || undefined,
      });
      setStage(updated);
      setModal(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleReasonOnlyAction(action: "REFER_SENIOR" | "REQUEST_CLARIFICATION") {
    setLoading(true);
    setError(null);
    try {
      const updated = await performStageAction(stage.id, { action, reason });
      setStage(updated);
      setModal(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const isActive = stage.status === "ACTIVE";

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3 md:px-6">
        <Link href="/officer/queue" className="text-xs text-muted hover:text-text">
          ← {t("backToQueue")}
        </Link>
        <div className="mt-2 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold text-text">{stage.app_no ?? stage.stage_key}</h1>
            <p className="text-sm text-muted">
              {stage.institution_name} · {stage.stage_key}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {stage.deadline && <SlaPill dueAt={stage.deadline.due_at} />}
            <StatusChip status={stage.status} />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {error && (
          <p className="mx-4 mt-4 rounded-lg bg-danger-soft px-3 py-2 text-sm text-danger md:mx-6">{error}</p>
        )}
        <div className="grid min-h-[480px] grid-cols-1 lg:grid-cols-[340px_minmax(0,1fr)_380px]">
          <CaseFilePanel stage={stage} application={application} stages={applicationStages} />
          <div className="min-h-[480px] border-b border-border lg:border-b-0 lg:border-r">
            <DocViewer documents={documents} onDocumentVerified={handleDocumentVerified} />
          </div>
          <AiPanel report={aiReport} />
        </div>
      </div>

      {isActive && (
        <ActionBar>
          <Button variant="ai" disabled title={t("aiAssistantComingSoon")}>
            <MessageSquareText className="size-4" />
            {t("actions.AI_ASSISTANT")}
          </Button>
          <span className="flex-1" />
          {stage.allowed_actions.includes("REQUEST_CLARIFICATION") && (
            <Button
              variant="outline"
              onClick={() => {
                setModal("REQUEST_CLARIFICATION");
                setReason("");
              }}
              disabled={loading}
            >
              {t("actions.REQUEST_CLARIFICATION")}
            </Button>
          )}
          {stage.allowed_actions.includes("REFER_SENIOR") && (
            <Button
              variant="outline"
              onClick={() => {
                setModal("REFER_SENIOR");
                setReason("");
              }}
              disabled={loading}
            >
              {t("actions.REFER_SENIOR")}
            </Button>
          )}
          {stage.allowed_actions.includes("RETURN") && (
            <Button variant="danger" onClick={openReturnModal} disabled={loading}>
              {t("actions.RETURN")}
            </Button>
          )}
          {stage.allowed_actions.includes("CLEAR") && (
            <Button onClick={handleClear} disabled={loading}>
              {t("actions.CLEAR")}
            </Button>
          )}
        </ActionBar>
      )}

      <Modal open={modal === "RETURN"} onOpenChange={(open) => !open && setModal(null)} title={t("returnModal.title")}>
        <div className="space-y-3">
          {stage.returns_count > 0 && (
            <p className="rounded-lg bg-warning-soft px-3 py-2 text-xs text-warning">
              {t("returnModal.maxReturnsWarning")}
            </p>
          )}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted">{t("returnModal.reasonLabel")}</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted">
              {t("returnModal.deficienciesLabel")}
            </label>
            <div className="flex gap-2">
              <input
                value={deficiencyText}
                onChange={(e) => setDeficiencyText(e.target.value)}
                placeholder={t("returnModal.customTextLabel")}
                className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (deficiencyText.trim()) {
                    setDeficiencies((prev) => [...prev, deficiencyText.trim()]);
                    setDeficiencyText("");
                  }
                }}
              >
                {t("returnModal.addDeficiency")}
              </Button>
            </div>
            <ul className="mt-2 space-y-1">
              {deficiencies.map((d, i) => (
                <li key={i} className="text-xs text-text">
                  • {d}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted">{t("returnModal.letterLabel")}</label>
            <textarea
              value={letterBody}
              onChange={(e) => setLetterBody(e.target.value)}
              rows={6}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setModal(null)}>
              {t("returnModal.cancel")}
            </Button>
            <Button variant="danger" onClick={handleReturn} disabled={loading || !reason || deficiencies.length === 0}>
              {t("returnModal.send")}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={modal === "REFER_SENIOR"}
        onOpenChange={(open) => !open && setModal(null)}
        title={t("referModal.title")}
      >
        <div className="space-y-3">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t("referModal.reasonLabel")}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setModal(null)}>
              {t("referModal.cancel")}
            </Button>
            <Button onClick={() => handleReasonOnlyAction("REFER_SENIOR")} disabled={loading || !reason}>
              {t("referModal.submit")}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={modal === "REQUEST_CLARIFICATION"}
        onOpenChange={(open) => !open && setModal(null)}
        title={t("clarifyModal.title")}
      >
        <div className="space-y-3">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={t("clarifyModal.reasonLabel")}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text"
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setModal(null)}>
              {t("clarifyModal.cancel")}
            </Button>
            <Button onClick={() => handleReasonOnlyAction("REQUEST_CLARIFICATION")} disabled={loading || !reason}>
              {t("clarifyModal.submit")}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

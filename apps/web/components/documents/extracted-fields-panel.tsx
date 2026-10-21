"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { type DocumentOut, verifyDocument } from "@/lib/api";
import { cn } from "@/lib/utils";

function confidenceTone(confidence: number): string {
  if (confidence >= 0.9) return "text-success";
  if (confidence >= 0.7) return "text-warning";
  return "text-danger";
}

function humanizeFieldName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Officer "verify extracted fields" interaction (IMPLEMENTATION.md Phase P3):
 * per-field accept/edit against the OCR extraction, persisted via
 * POST /documents/{id}/verify, which marks each submitted field
 * `human_verified` and re-runs the application's AI checks.
 */
export function ExtractedFieldsPanel({
  document: doc,
  onVerified,
}: {
  document: DocumentOut;
  onVerified: (updated: DocumentOut) => void;
}) {
  const t = useTranslations("caseReview.extractedFields");
  const extraction = doc.extraction;
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    setValues(Object.fromEntries(Object.entries(extraction?.fields ?? {}).map(([k, v]) => [k, v.value])));
    setError(false);
  }, [doc.id, extraction]);

  if (!extraction || Object.keys(extraction.fields).length === 0) {
    return null;
  }

  const fieldNames = Object.keys(extraction.fields);

  async function handleSave() {
    setSaving(true);
    setError(false);
    try {
      const updated = await verifyDocument(doc.id, { fields: values, result: "VERIFIED" });
      onVerified(updated);
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="border-t border-border bg-surface">
      <div className="flex items-center justify-between px-3 py-2">
        <p className="text-xs font-semibold text-muted">{t("title")}</p>
        {doc.verified_status === "VERIFIED" && (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-success">
            <ShieldCheck className="size-3" aria-hidden />
            {t("verified")}
          </span>
        )}
      </div>
      <div className="max-h-56 space-y-2 overflow-y-auto px-3 pb-3">
        {fieldNames.map((name) => {
          const field = extraction.fields[name];
          return (
            <div key={name} className="flex items-center gap-2">
              <label className="w-32 shrink-0 truncate text-xs text-muted" title={name}>
                {humanizeFieldName(name)}
              </label>
              <input
                value={values[name] ?? ""}
                onChange={(e) => setValues((prev) => ({ ...prev, [name]: e.target.value }))}
                className="min-w-0 flex-1 rounded-lg border border-border bg-surface-2 px-2 py-1 text-sm text-text"
              />
              <span className={cn("w-10 shrink-0 text-right text-xs font-medium", confidenceTone(field.confidence))}>
                {Math.round(field.confidence * 100)}%
              </span>
              {field.human_verified && <CheckCircle2 className="size-3.5 shrink-0 text-success" aria-hidden />}
            </div>
          );
        })}
      </div>
      {error && <p className="px-3 pb-2 text-xs text-danger">{t("saveError")}</p>}
      <div className="flex justify-end border-t border-border px-3 py-2">
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving && <Loader2 className="size-3.5 animate-spin" />}
          {t("saveVerification")}
        </Button>
      </div>
    </div>
  );
}

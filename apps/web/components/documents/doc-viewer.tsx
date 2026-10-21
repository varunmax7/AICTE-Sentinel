"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { Columns2, RotateCw, ShieldCheck, ZoomIn, ZoomOut } from "lucide-react";

import { AiBadge } from "@/components/status/ai-badge";
import { Button } from "@/components/ui/button";
import { type DocumentOut, documentAssetUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

import { ExtractedFieldsPanel } from "./extracted-fields-panel";

function PagePreview({ document: doc }: { document: DocumentOut }) {
  const t = useTranslations("caseReview.docViewer");
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);

  const pageCount = doc.extraction?.page_count ?? 1;
  const boxes = (doc.extraction?.boxes ?? []).filter((b) => b.page === 1);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <span className="text-xs text-muted">{t("pageOf", { page: 1, total: pageCount })}</span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
            className="rounded p-1 text-muted hover:bg-surface-2 hover:text-text"
            aria-label={t("zoomOut")}
          >
            <ZoomOut className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
            className="rounded p-1 text-muted hover:bg-surface-2 hover:text-text"
            aria-label={t("zoomIn")}
          >
            <ZoomIn className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => setRotation((r) => (r + 90) % 360)}
            className="rounded p-1 text-muted hover:bg-surface-2 hover:text-text"
            aria-label={t("rotate")}
          >
            <RotateCw className="size-4" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto bg-surface-2 p-4">
        {doc.preview_url ? (
          <div
            className="relative mx-auto w-fit origin-top transition-transform"
            style={{ transform: `scale(${zoom}) rotate(${rotation}deg)` }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- backend-streamed, not a Next static asset */}
            <img src={documentAssetUrl(doc.preview_url)} alt="" className="block max-w-full shadow-sm" />
            {boxes.map((box, i) => (
              <span
                key={i}
                title={box.label}
                className={cn(
                  "absolute border-2",
                  box.status === "matched" ? "border-success/70 bg-success/10" : "border-warning/70 bg-warning/10"
                )}
                style={{
                  left: `${box.x * 100}%`,
                  top: `${box.y * 100}%`,
                  width: `${box.w * 100}%`,
                  height: `${box.h * 100}%`,
                }}
              />
            ))}
          </div>
        ) : (
          <p className="p-6 text-center text-sm text-muted">{t("noPreview")}</p>
        )}
      </div>
    </div>
  );
}

export function DocViewer({
  documents,
  onDocumentVerified,
}: {
  documents: DocumentOut[];
  onDocumentVerified?: (updated: DocumentOut) => void;
}) {
  const t = useTranslations("caseReview.docViewer");
  const [selectedId, setSelectedId] = useState(documents[0]?.id);
  const [compareId, setCompareId] = useState<string | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);

  const selected = documents.find((d) => d.id === selectedId);
  const compareDoc = documents.find((d) => d.id === compareId);

  if (documents.length === 0) {
    return <p className="flex h-full items-center justify-center text-sm text-muted">{t("noDocuments")}</p>;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1 overflow-x-auto border-b border-border px-3 py-2">
        {documents.map((doc) => (
          <button
            key={doc.id}
            onClick={() => setSelectedId(doc.id)}
            className={cn(
              "shrink-0 rounded-full border px-3 py-1 text-xs font-medium",
              doc.id === selectedId
                ? "border-primary bg-ai-soft text-primary"
                : "border-border text-muted hover:bg-surface-2"
            )}
          >
            {doc.document_type}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          {selected?.verified_status === "VERIFIED" && (
            <span className="inline-flex items-center gap-1 rounded-full bg-success-soft px-2 py-0.5 text-xs font-medium text-success">
              <ShieldCheck className="size-3" aria-hidden />
              {t("aiOcrVerified")}
            </span>
          )}
          {selected?.extraction && <AiBadge />}
          {documents.length > 1 && (
            <Button
              size="sm"
              variant={compareOpen ? "ai" : "outline"}
              onClick={() => {
                setCompareOpen((v) => !v);
                if (!compareId) setCompareId(documents.find((d) => d.id !== selectedId)?.id ?? null);
              }}
            >
              <Columns2 className="size-3.5" />
              {t("compare")}
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {compareOpen && compareDoc ? (
          <div className="grid h-full grid-cols-2 divide-x divide-border">
            {selected && <PagePreview document={selected} />}
            <div className="flex h-full flex-col">
              <select
                value={compareId ?? ""}
                onChange={(e) => setCompareId(e.target.value)}
                className="border-b border-border bg-surface px-3 py-2 text-xs text-text"
              >
                {documents
                  .filter((d) => d.id !== selectedId)
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.document_type}
                    </option>
                  ))}
              </select>
              <div className="flex-1">{compareDoc && <PagePreview document={compareDoc} />}</div>
            </div>
          </div>
        ) : (
          selected && (
            <div className="flex h-full flex-col">
              <div className="flex-1 overflow-hidden">
                <PagePreview document={selected} />
              </div>
              {onDocumentVerified && (
                <ExtractedFieldsPanel document={selected} onVerified={onDocumentVerified} />
              )}
            </div>
          )
        )}
      </div>
    </div>
  );
}

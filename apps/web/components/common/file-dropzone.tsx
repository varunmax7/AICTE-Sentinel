"use client";

import { Upload } from "lucide-react";
import { useCallback, useId, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Drag-drop file input with basic progress/status display (IMPLEMENTATION.md
 * §7.5). The actual upload call (`POST /documents`, OCR status polling) is
 * wired in by each caller starting Phase P3 — this component only emits the
 * picked files.
 */
export function FileDropzone({
  onFiles,
  accept,
  multiple = true,
  status,
  className,
}: {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  status?: { label: string; progress?: number } | null;
  className?: string;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      onFiles(Array.from(fileList));
    },
    [onFiles]
  );

  return (
    <div
      className={cn(
        "rounded-xl border-2 border-dashed border-border bg-surface-2 p-6 text-center transition-colors",
        dragging && "border-primary bg-ai-soft",
        className
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <label htmlFor={inputId} className="flex cursor-pointer flex-col items-center gap-2">
        <Upload className="size-6 text-muted" aria-hidden />
        <span className="text-sm text-text">Drag & drop, or click to choose files</span>
      </label>
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {status && (
        <div className="mt-4">
          <p className="text-xs text-muted">{status.label}</p>
          {typeof status.progress === "number" && (
            <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.max(0, Math.min(100, status.progress))}%` }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

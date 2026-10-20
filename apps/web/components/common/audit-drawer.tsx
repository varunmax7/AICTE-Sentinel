"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import type { TimelineEntry } from "./timeline";
import { Timeline } from "./timeline";

/**
 * Right drawer listing hash-chained audit events for an entity
 * (IMPLEMENTATION.md §7.5, §16). Takes already-fetched entries — wiring to
 * `GET /audit?entity_type&entity_id` lands with the P10 admin audit explorer.
 */
export function AuditDrawer({
  open,
  onOpenChange,
  title,
  entries,
  trigger,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  entries: TimelineEntry[];
  trigger?: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content
          className={cn(
            "fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-surface p-6 shadow-xl",
            "data-[state=open]:animate-in data-[state=open]:slide-in-from-right"
          )}
        >
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold text-text">{title}</Dialog.Title>
            <Dialog.Close className="rounded-full p-1.5 text-muted hover:bg-surface-2 hover:text-text">
              <X className="size-4" />
            </Dialog.Close>
          </div>
          <div className="flex-1 overflow-y-auto">
            {entries.length === 0 ? (
              <p className="text-sm text-muted">No audit events yet.</p>
            ) : (
              <Timeline entries={entries} />
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

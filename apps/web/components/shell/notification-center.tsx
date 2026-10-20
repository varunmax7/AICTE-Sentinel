"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Bell, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useEventStream } from "@/lib/sse";

import { IconBadge } from "../status/icon-badge";

/**
 * Bell icon + drawer, live over SSE (`GET /api/v1/stream`, §4.1). Phase P1
 * broadcasts globally (see docs/DECISIONS.md) so every event the viewer
 * receives is shown here, unread-counted by "seen since opened" rather than
 * a real per-notification read state (that lands with the P7 notification
 * orchestrator and its `notifications`/`notification_deliveries` tables).
 */
export function NotificationCenter() {
  const t = useTranslations("notifications");
  const [open, setOpen] = useState(false);
  const { connected, events } = useEventStream(true);
  const [seenCount, setSeenCount] = useState(0);

  const unread = Math.max(0, events.length - seenCount);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) setSeenCount(events.length);
      }}
    >
      <Dialog.Trigger asChild>
        <IconBadge icon={Bell} count={unread} label={t("title")} />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col border-l border-border bg-surface p-5 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Dialog.Title className="text-base font-semibold text-text">{t("title")}</Dialog.Title>
              <span
                className={`size-1.5 rounded-full ${connected ? "bg-success" : "bg-muted"}`}
                title={connected ? t("liveConnected") : t("liveDisconnected")}
              />
            </div>
            <Dialog.Close className="rounded-full p-1.5 text-muted hover:bg-surface-2 hover:text-text">
              <X className="size-4" />
            </Dialog.Close>
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto">
            {events.length === 0 ? (
              <p className="text-sm text-muted">{t("empty")}</p>
            ) : (
              events.map((event, i) => (
                <div key={`${event.event}-${event.at}-${i}`} className="rounded-lg border border-border p-3">
                  <p className="text-sm font-medium text-text">{event.event}</p>
                  <p className="mt-0.5 text-xs text-muted">{new Date(event.at).toLocaleString()}</p>
                </div>
              ))
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

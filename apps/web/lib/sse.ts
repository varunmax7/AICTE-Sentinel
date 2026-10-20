"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface SseEvent {
  event: string;
  payload: Record<string, unknown>;
  at: string;
}

/**
 * Subscribes to the core API's SSE stream (`/api/v1/stream`, §4.1) for as
 * long as the component is mounted. Treats every message as "something
 * happened, go refetch" — it does not assume the payload is addressed to
 * this viewer specifically (see docs/DECISIONS.md on per-recipient
 * targeting arriving in Phase P7).
 */
export function useEventStream(enabled: boolean) {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<SseEvent[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const source = new EventSource(`${API_BASE}/api/v1/stream`, { withCredentials: true });
    sourceRef.current = source;

    source.addEventListener("connected", () => setConnected(true));
    source.addEventListener("message", (e: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(e.data) as SseEvent;
        setEvents((prev) => [parsed, ...prev].slice(0, 50));
      } catch {
        // ignore malformed payloads
      }
    });
    source.onerror = () => setConnected(false);

    return () => {
      source.close();
      sourceRef.current = null;
      setConnected(false);
    };
  }, [enabled]);

  return { connected, events };
}

"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RunStatus } from "@/types";

export const POLL_INTERVAL_MS = 900;
const MAX_BACKOFF_MS = 5000;

export interface PollState {
  status: RunStatus | null;
  done: boolean;
  failed: boolean;
  error: string | null;
}

/** Poll GET /api/runs/{id} until a terminal status. No fake progress —
 *  every update comes from the backend's persisted run state. */
export function useRunPolling(runId: string | null, nonce = 0): PollState {
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const failures = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setStatus(null);
    setError(null);
    failures.current = 0;
    if (!runId) return;
    let cancelled = false;

    async function tick() {
      try {
        const next = await api.getRunStatus(runId as string);
        if (cancelled) return;
        failures.current = 0;
        setStatus(next);
        if (next.status === "completed" || next.status === "failed") return;
        timer.current = setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        failures.current += 1;
        if (failures.current >= 4) {
          setError(err instanceof Error ? err.message : "Lost contact with the backend.");
          return;
        }
        const backoff = Math.min(POLL_INTERVAL_MS * 2 ** failures.current, MAX_BACKOFF_MS);
        timer.current = setTimeout(tick, backoff);
      }
    }
    tick();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [runId, nonce]);

  return {
    status,
    done: status?.status === "completed",
    failed: status?.status === "failed",
    error,
  };
}

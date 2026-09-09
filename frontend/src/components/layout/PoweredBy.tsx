"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Integrations {
  gemini_configured?: boolean;
  google_cloud_project_set?: boolean;
  parallel_configured?: boolean;
  model?: string;
}

/** Subtle technology attribution reflecting live backend configuration. */
export function PoweredBy() {
  const [integrations, setIntegrations] = useState<Integrations | null>(null);
  useEffect(() => {
    let cancelled = false;
    api
      .getStatus()
      .then((s) => {
        if (cancelled) return;
        const integ = (s as { integrations?: Integrations })?.integrations ?? null;
        setIntegrations(integ);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  const parts = [
    `Gemini${integrations ? (integrations.gemini_configured ? " · live" : " · standby") : ""}`,
    integrations?.google_cloud_project_set ? "Google Cloud · connected" : "Google Cloud",
    `Parallel Search${integrations ? (integrations.parallel_configured ? " · live" : " · standby") : ""}`,
  ];
  return (
    <p className="powered-by" aria-label="Powered by">
      Powered by {parts.join(" · ")}
      {integrations?.model ? ` · ${integrations.model}` : ""}
    </p>
  );
}

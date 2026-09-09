"use client";

import type { BackendStatus, Project } from "@/types";

const DOT_LABEL: Record<BackendStatus, string> = {
  checking: "Checking backend…",
  online: "Backend online",
  offline: "Backend offline",
};

export function TopBar({
  projectName,
  status,
  backendStatus,
  isFixture,
  projects,
  activeProjectId,
  onSelectProject,
  onNewAnalysis,
}: {
  projectName: string;
  status: string;
  backendStatus: BackendStatus;
  isFixture: boolean;
  projects?: Project[];
  activeProjectId?: string | null;
  onSelectProject?: (projectId: string) => void;
  onNewAnalysis: () => void;
}) {
  return (
    <header className="site-header">
      <div className="wrap header-inner">
        <div>
          <p className="brand">CINEGUARD</p>
          <p className="brand-sub">Production Intelligence</p>
        </div>
        <div className="topbar-mid">
          {projects && projects.length > 0 && onSelectProject ? (
            <label className="project-select">
              <span className="sr-only">Active project</span>
              <select
                value={activeProjectId ?? ""}
                onChange={(e) => {
                  if (e.target.value) onSelectProject(e.target.value);
                }}
                aria-label="Active project"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.latest_run_status ? ` · ${p.latest_run_status}` : ""}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <span className="project-name" title="Active project">
              {projectName}
            </span>
          )}
          <span className="badge badge-neutral">{status}</span>
          {isFixture ? (
            <span className="badge badge-warn" title="Sample data for UI testing only">
              SAMPLE DATA
            </span>
          ) : null}
        </div>
        <div className="topbar-right">
          <div className="backend-pill" role="status" aria-label={DOT_LABEL[backendStatus]}>
            <span className={`dot dot-${backendStatus}`} aria-hidden="true" />
            <span>{DOT_LABEL[backendStatus]}</span>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onNewAnalysis}>
            New analysis
          </button>
        </div>
      </div>
    </header>
  );
}

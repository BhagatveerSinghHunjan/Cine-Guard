import type { BackendStatus } from "@/types";

const DOT_LABEL: Record<BackendStatus, string> = {
  checking: "Checking backend…",
  online: "Backend online",
  offline: "Backend offline",
};

export function Header({ backendStatus }: { backendStatus: BackendStatus }) {
  return (
    <header className="site-header">
      <div className="wrap header-inner">
        <div>
          <p className="brand">CINEGUARD</p>
          <p className="brand-sub">Production Intelligence</p>
        </div>
        <div className="backend-pill" role="status" aria-label={DOT_LABEL[backendStatus]}>
          <span className={`dot dot-${backendStatus}`} aria-hidden="true" />
          <span>{DOT_LABEL[backendStatus]}</span>
        </div>
      </div>
    </header>
  );
}

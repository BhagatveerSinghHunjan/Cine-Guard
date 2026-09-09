"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnalysisProgress } from "@/components/analysis/AnalysisProgress";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { Header } from "@/components/layout/Header";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProjectNameField } from "@/components/upload/ProjectNameField";
import { UploadCard } from "@/components/upload/UploadCard";
import { api, friendlyErrorMessage } from "@/lib/api";
import { extractTextFromFile } from "@/lib/screenplay";
import { stageIndexForRun } from "@/lib/stages";
import { useRunPolling } from "@/lib/useRunPolling";
import type { AnalyzeResponse, BackendStatus, Project, RunStatus } from "@/types";

type Phase = "upload" | "tracking" | "results";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("");
  const [apiError, setApiError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [retryNonce, setRetryNonce] = useState(0);
  const [isFixture, setIsFixture] = useState(false);
  const [demoText, setDemoText] = useState<string | null>(null);
  const [demoTitle, setDemoTitle] = useState("");
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [projects, setProjects] = useState<Project[]>([]);
  const resultsRef = useRef<HTMLDivElement>(null);

  const poll = useRunPolling(phase === "tracking" ? runId : null, retryNonce);

  useEffect(() => {
    api
      .getHealth()
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  // Real backend state drives everything: completed → results, failed → error UI.
  useEffect(() => {
    if (phase !== "tracking") return;
    if (poll.status) setRunStatus(poll.status);
    if (poll.done && poll.status?.result) {
      setResult(poll.status.result);
      setIsFixture(false);
      setPhase("results");
    }
  }, [phase, poll.status, poll.done]);

  useEffect(() => {
    if (phase === "results" && result) {
      document.getElementById("results-heading")?.focus();
      api
        .listProjects()
        .then(setProjects)
        .catch(() => setProjects([]));
    }
  }, [phase, result]);

  const canAnalyze = (file !== null || demoText !== null) && phase !== "tracking";

  const handleAnalyze = useCallback(async () => {
    setApiError(null);
    setFileError(null);
    setRunStatus(null);
    setPhase("tracking");

    try {
      // Real local file read (or loaded demo input), then hand off to the
      // backend run pipeline. Results arrive only via run polling.
      const text = file ? await extractTextFromFile(file) : demoText ?? "";
      if (!text.trim()) {
        throw new Error("No screenplay content to analyze.");
      }
      const accepted = await api.postAnalyze({
        screenplay_text: text,
        project_title: projectName.trim() || (file ? file.name.replace(/\.[^.]+$/, "") : demoTitle),
      });
      setRunId(accepted.run_id);
    } catch (err) {
      setApiError(friendlyErrorMessage(err));
      setPhase("upload");
    }
  }, [file, demoText, demoTitle, projectName]);

  const handleRetry = useCallback(async () => {
    if (!runId) return;
    setApiError(null);
    try {
      await api.retryRun(runId);
      setRetryNonce((n) => n + 1);
    } catch (err) {
      setApiError(friendlyErrorMessage(err));
    }
  }, [runId]);

  const handleSelectProject = useCallback(async (projectId: string) => {
    try {
      const runs = await api.getProjectRuns(projectId);
      const latest = runs.find((r) => r.has_results) ?? runs[0];
      if (!latest) return;
      const status = await api.getRunStatus(latest.run_id);
      if (status.result) {
        setResult(status.result);
        setRunStatus(status);
        setRunId(status.run_id);
        setIsFixture(false);
        setPhase("results");
      }
    } catch (err) {
      setApiError(friendlyErrorMessage(err));
    }
  }, []);

  const handleReset = useCallback(() => {
    setResult(null);
    setRunStatus(null);
    setRunId(null);
    setIsFixture(false);
    setApiError(null);
    setFile(null);
    setDemoText(null);
    setDemoTitle("");
    setPhase("upload");
  }, []);

  /** Demo production: fictional screenplay loaded as *input* through the real
   *  analysis pipeline — never pre-computed results. */
  const handleLoadDemo = useCallback(async () => {
    setDemoError(null);
    setFileError(null);
    setApiError(null);
    setDemoLoading(true);
    try {
      const demo = await api.getDemoScreenplay();
      setDemoText(demo.screenplay_text);
      setDemoTitle(demo.title);
      setProjectName(demo.title);
      setFile(null);
    } catch (err) {
      setDemoError(friendlyErrorMessage(err));
    } finally {
      setDemoLoading(false);
    }
  }, []);

  const handleRemoveDemo = useCallback(() => {
    setDemoText(null);
    setDemoTitle("");
  }, []);

  const failed = poll.failed && poll.status;
  const tracking = phase === "tracking" && !failed;

  return (
    <>
      <Header backendStatus={backendStatus} />
      <main className="wrap">
        <section className="hero" aria-labelledby="hero-heading">
          <p className="eyebrow">CineGuard · Production Intelligence</p>
          <h1 id="hero-heading">Can this screenplay realistically move into production?</h1>
          <p className="lede">
            Upload a screenplay and let CineGuard identify production risks, dependencies, and
            scheduling blockers — before they break the shoot.
          </p>
        </section>

        {phase === "results" && result ? (
          <div ref={resultsRef}>
            <Dashboard
              result={result}
              runStatus={runStatus}
              backendStatus={backendStatus}
              isFixture={isFixture}
              projects={projects}
              onSelectProject={handleSelectProject}
              onReset={handleReset}
            />
          </div>
        ) : phase === "tracking" ? (
          failed && poll.status ? (
            <Card title="Analysis failed" labelledBy="analyzing-failed">
              <h2 id="analyzing-failed" className="card-title">
                Analysis failed during {failedStageLabel(poll.status)}
              </h2>
              <Alert variant="error" title={poll.status.error?.code ?? "Run failed"}>
                <p>{poll.status.error?.message ?? "The analysis run failed."}</p>
              </Alert>
              <p className="muted">
                {runId ? `Run ${runId} · attempt ${poll.status.attempt ?? 1}. ` : ""}
                Completed stages are preserved — retry restarts the same run without duplicating
                anything.
              </p>
              <Button variant="primary" onClick={handleRetry}>
                Retry analysis
              </Button>{" "}
              <Button variant="ghost" onClick={handleReset}>
                Start over
              </Button>
              {apiError ? (
                <Alert variant="error" title="Retry failed">
                  <p>{apiError}</p>
                </Alert>
              ) : null}
            </Card>
          ) : (
            <Card title="Analyzing production" labelledBy="analyzing-heading">
              <h2 id="analyzing-heading" className="card-title">
                Analyzing {projectName.trim() || file?.name || "screenplay"}…
              </h2>
              <p className="muted">
                {runStatus
                  ? `Stage: ${humanStage(runStatus)} · ${runStatus.progress ?? 0}% — live backend state, polled.`
                  : "Preparing screenplay and starting the backend run…"}
              </p>
              <AnalysisProgress
                activeIndex={Math.min(
                  stageIndexForRun(runStatus?.status, runStatus?.current_stage),
                  4,
                )}
              />
              {poll.error ? (
                <Alert variant="error" title="Lost contact with the backend">
                  <p>{poll.error}</p>
                </Alert>
              ) : null}
            </Card>
          )
        ) : (
          <div className="grid-2">
            <UploadCard
              file={file}
              error={fileError}
              onSelect={(f) => {
                setFile(f);
                setFileError(null);
                setApiError(null);
              }}
              onError={(m) => {
                setFile(null);
                setFileError(m);
              }}
              onRemove={() => {
                setFile(null);
                setFileError(null);
              }}
            />
            <Card title="Production setup" labelledBy="setup-title">
              <h2 id="setup-title" className="card-title">
                Production setup
              </h2>
              <ProjectNameField value={projectName} onChange={setProjectName} />
              <Button
                variant="primary"
                disabled={!canAnalyze}
                onClick={handleAnalyze}
                aria-disabled={!canAnalyze}
                title={!file && !demoText ? "Select a screenplay file or load the demo" : undefined}
              >
                Analyze Production
              </Button>
              {!file && !demoText ? (
                <p className="muted cta-note">
                  Select a screenplay file, or run the fictional demo production through the real
                  pipeline.
                </p>
              ) : null}
              {demoText && !file ? (
                <div className="demo-input" role="status">
                  <p>
                    <span className="badge badge-warn">DEMO INPUT · FICTIONAL</span>
                  </p>
                  <p className="file-name">{demoTitle || "Demo production"}</p>
                  <p className="muted">
                    {demoText.length.toLocaleString()} characters · runs the real analysis pipeline,
                    nothing pre-computed.
                  </p>
                  <button type="button" className="link-btn" onClick={handleRemoveDemo}>
                    Remove demo input
                  </button>
                </div>
              ) : null}
              <p className="muted cta-note">
                No file handy?{" "}
                <button
                  type="button"
                  className="link-btn"
                  onClick={handleLoadDemo}
                  disabled={demoLoading}
                >
                  {demoLoading ? "Loading demo…" : "Load Demo Production"}
                </button>{" "}
                (fictional screenplay, analyzed live).
              </p>
              {demoError ? (
                <Alert variant="error" title="Demo unavailable">
                  <p>{demoError}</p>
                </Alert>
              ) : null}
              {apiError ? (
                <Alert variant="error" title="Analysis failed">
                  <p>{apiError}</p>
                  <Button variant="ghost" onClick={handleAnalyze} disabled={!file}>
                    Retry
                  </Button>
                </Alert>
              ) : null}
            </Card>
          </div>
        )}

        <footer className="footer">
          <p>
            UPLOAD → ANALYZE → UNDERSTAND RESULTS → FIX PRODUCTION · Backend-driven scores, never
            hardcoded.
          </p>
        </footer>
      </main>
    </>
  );
}

function humanStage(status: { current_stage?: string; status: string }): string {
  const stage = status.current_stage || status.status;
  return stage.replace(/_/g, " ");
}

function failedStageLabel(status: { error?: { stage?: string } | null }): string {
  const stage = status.error?.stage;
  return stage ? humanStage({ current_stage: stage, status: "" }) : "the analysis";
}

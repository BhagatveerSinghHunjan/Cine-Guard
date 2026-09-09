"use client";

import { useState } from "react";
import { Overview } from "@/components/dashboard/Overview";
import { DependencyGraph } from "@/components/dependencies/DependencyGraph";
import { DetailDrawer } from "@/components/layout/DetailDrawer";
import { PoweredBy } from "@/components/layout/PoweredBy";
import { TopBar } from "@/components/layout/TopBar";
import { PlanWorkspace } from "@/components/planning/PlanWorkspace";
import { ResearchPanel } from "@/components/research/ResearchPanel";
import { RiskBoard } from "@/components/risks/Risks";
import { RiskDetail } from "@/components/risks/RiskDetail";
import { SceneDetail, SceneList } from "@/components/scenes/SceneList";
import type { AnalyzeResponse, BackendStatus, FixPlan, Project, RunStatus } from "@/types";

type Tab = "overview" | "scenes" | "risks" | "dependencies" | "research" | "plan";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "scenes", label: "Scenes" },
  { id: "risks", label: "Risks" },
  { id: "dependencies", label: "Dependencies" },
  { id: "research", label: "Research" },
  { id: "plan", label: "Plan" },
];

export function Dashboard({
  result,
  runStatus,
  backendStatus,
  isFixture,
  projects,
  onSelectProject,
  onReset,
}: {
  result: AnalyzeResponse;
  runStatus: RunStatus | null;
  backendStatus: BackendStatus;
  isFixture: boolean;
  projects: Project[];
  onSelectProject: (projectId: string) => void;
  onReset: () => void;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [riskId, setRiskId] = useState<string | null>(null);
  const [sceneNumber, setSceneNumber] = useState<number | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [plan, setPlan] = useState<FixPlan | null>(null);
  const [planning, setPlanning] = useState(false);

  const risk = result.risks.find((r) => r.id === riskId) ?? null;
  const scene = result.analysis.scenes.find((s) => s.scene_number === sceneNumber) ?? null;
  const status = result.readiness?.status ?? "—";

  function openRisk(id: string) {
    setSceneNumber(null);
    setRiskId(id);
  }
  function openScene(n: number) {
    setRiskId(null);
    setSceneNumber(n);
  }
  function closeDrawer() {
    setRiskId(null);
    setSceneNumber(null);
  }
  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <>
      <TopBar
        projectName={result.project_title}
        status={status}
        backendStatus={backendStatus}
        isFixture={isFixture}
        projects={projects}
        activeProjectId={runStatus?.project_id ?? null}
        onSelectProject={onSelectProject}
        onNewAnalysis={onReset}
      />
      <main className="wrap">
        {isFixture ? (
          <p className="sample-banner" role="note">
            SAMPLE DATA — isolated UI fixture for testing. Not a production analysis.
          </p>
        ) : null}
        <nav className="dash-nav" aria-label="Dashboard sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
            >
              {t.label}
              {t.id === "risks" ? ` (${result.risks.length})` : ""}
              {t.id === "scenes" ? ` (${result.analysis.scenes.length})` : ""}
            </button>
          ))}
        </nav>

        {tab === "overview" ? (
          <Overview
            result={result}
            events={runStatus?.events ?? []}
            planning={planning}
            setPlanning={setPlanning}
            planned={plan !== null}
            plan={plan}
            setPlan={setPlan}
            selected={selected}
            onToggleSelect={toggle}
            onSelectRisk={openRisk}
          />
        ) : null}
        {tab === "scenes" ? <SceneList result={result} onSelectScene={openScene} /> : null}
        {tab === "risks" ? (
          <RiskBoard risks={result.risks} scenes={result.analysis.scenes} onSelect={openRisk} />
        ) : null}
        {tab === "dependencies" ? (
          <DependencyGraph result={result} onSelectRisk={openRisk} onSelectScene={openScene} />
        ) : null}
        {tab === "research" ? <ResearchPanel result={result} onSelectRisk={openRisk} /> : null}
        {tab === "plan" ? (
          <PlanWorkspace
            result={result}
            selected={selected}
            onToggle={toggle}
            plan={plan}
            setPlan={setPlan}
            planning={planning}
            setPlanning={setPlanning}
          />
        ) : null}

        <footer className="footer">
          <p>
            UPLOAD → ANALYZE → INVESTIGATE → DECIDE → MITIGATE · Backend-driven scores, never
            hardcoded.
          </p>
          <PoweredBy />
        </footer>
      </main>

      {risk ? (
        <DetailDrawer title={`Risk ${risk.id}`} onClose={closeDrawer}>
          <RiskDetail
            risk={risk}
            result={result}
            onSelectRisk={openRisk}
            onSelectScene={openScene}
          />
        </DetailDrawer>
      ) : null}
      {scene && !risk ? (
        <DetailDrawer title={`Scene ${scene.scene_number}`} onClose={closeDrawer}>
          <SceneDetail scene={scene} result={result} onSelectRisk={openRisk} />
        </DetailDrawer>
      ) : null}
    </>
  );
}

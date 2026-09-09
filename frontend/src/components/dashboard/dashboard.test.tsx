import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { sampleAnalyzeResponse, samplePlanResponse } from "@/lib/devFixture";

const { mockPostPlan } = vi.hoisted(() => ({ mockPostPlan: vi.fn() }));

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...mod,
    api: {
      getHealth: vi.fn(),
      getStatus: vi.fn().mockResolvedValue({ integrations: {} }),
      postAnalyze: vi.fn(),
      postPlan: mockPostPlan,
    },
    friendlyErrorMessage: (e: unknown) => (e instanceof Error ? e.message : "Error"),
  };
});

function renderDashboard() {
  return render(
    <Dashboard
      result={sampleAnalyzeResponse()}
      runStatus={null}
      backendStatus="online"
      isFixture
      projects={[]}
      onSelectProject={vi.fn()}
      onReset={vi.fn()}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Command Center", () => {
  it("renders readiness score and deterministic explanation on overview", () => {
    renderDashboard();
    expect(screen.getByText("77.5%")).toBeInTheDocument();
    expect(screen.getByText("AT RISK")).toBeInTheDocument();
    expect(screen.getByText(/blocked by 1 critical/i)).toBeInTheDocument();
  });

  it("filters risks by severity on the Risks tab", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /risks/i }));
    await user.click(screen.getByRole("button", { name: /critical \(1\)/i }));
    expect(screen.getByText(/rooftop\/helicopter access/i)).toBeInTheDocument();
    expect(screen.queryByText(/harbor chase needs coordinator/i)).not.toBeInTheDocument();
  });

  it("opens a risk detail panel with evidence and dependencies", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /risks/i }));
    const card = screen.getByLabelText(/critical risk: Rooftop/i);
    await user.click(within(card).getByRole("button", { name: /open details/i }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/why this matters/i)).toBeInTheDocument();
    expect(within(dialog).getAllByText("SCREENPLAY FACT").length).toBeGreaterThanOrEqual(1);
    expect(within(dialog).getByText("INFERENCE", { selector: "span" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /R-002.*blocks/ })).toBeInTheDocument();
  });

  it("filters scenes by risk level and shows scene detail", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /scenes/i }));
    await user.click(screen.getByRole("button", { name: /^high risk$/i }));
    expect(screen.getByRole("button", { name: /open scene 2/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open scene 4/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open scene 2/i }));
    expect(screen.getByRole("dialog")).toHaveTextContent(/associated risks \(2\)/i);
  });

  it("renders Parallel research with sources and error states", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /research/i }));
    expect(screen.getByText(/harbor film office/i)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /harborfilm\.example\/permits/ });
    expect(link).toHaveAttribute("target", "_blank");
    expect(screen.getByText(/research unavailable for this query/i)).toBeInTheDocument();
  });

  it("builds a fix plan successfully from the Plan tab", async () => {
    const user = userEvent.setup();
    mockPostPlan.mockResolvedValueOnce(samplePlanResponse());
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /plan/i }));
    await user.click(screen.getByRole("checkbox", { name: /rooftop access/i }));
    await user.click(screen.getByRole("checkbox", { name: /harbor stunt/i }));
    await user.click(screen.getByRole("button", { name: /build revised production plan \(2\)/i }));
    await waitFor(() => expect(screen.getByText("97.5%")).toBeInTheDocument());
    expect(mockPostPlan).toHaveBeenCalledWith("run-sample-fixture", ["REC-001", "REC-002"]);
    expect(screen.getByRole("columnheader", { name: /recommended change/i })).toBeInTheDocument();
    expect(screen.getByText(/production blockers remaining/i)).toBeInTheDocument();
  });

  it("surfaces plan API failures without fake success", async () => {
    const user = userEvent.setup();
    mockPostPlan.mockRejectedValueOnce(new Error("plan exploded"));
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /plan/i }));
    await user.click(screen.getByRole("checkbox", { name: /rooftop access/i }));
    await user.click(screen.getByRole("button", { name: /build revised production plan \(1\)/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/plan exploded/i);
    expect(screen.queryByText(/after mitigation/i)).not.toBeInTheDocument();
  });

  it("renders real activity events and unknowns in risk detail", async () => {
    const user = userEvent.setup();
    const { sampleAnalyzeResponse } = await import("@/lib/devFixture");
    const { Dashboard: Dash } = await import("@/components/dashboard/Dashboard");
    render(
      <Dash
        result={sampleAnalyzeResponse()}
        runStatus={{
          run_id: "run-x",
          status: "completed",
          events: [
            {
              seq: 1,
              ts: "2026-09-09T14:32:08+00:00",
              type: "screenplay_parsed",
              message: "Screenplay parsed",
            },
            {
              seq: 2,
              ts: "2026-09-09T14:32:14+00:00",
              type: "parallel_search_completed",
              message: "Parallel Search finished: 1/2 with sources",
            },
          ],
        }}
        backendStatus="online"
        isFixture={false}
        projects={[]}
        onSelectProject={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    expect(screen.getByText(/screenplay parsed/i)).toBeInTheDocument();
    expect(screen.getByText(/parallel search finished/i)).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /risks/i }));
    const card = screen.getByLabelText(/critical risk: Rooftop/i);
    await user.click(within(card).getByRole("button", { name: /open details/i }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/what we know/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/what we don't know/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/aerial permit.*unknown/i)).toBeInTheDocument();
  });

  it("expands the readiness breakdown with real backend lines", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(
      screen.getByRole("button", {
        name: /production readiness 77\.5 percent.*show score breakdown/i,
      }),
    );
    expect(screen.getByText(/base readiness/i)).toBeInTheDocument();
    expect(screen.getByText(/−15\.0/)).toBeInTheDocument();
    expect(screen.getByText(/−5\.0/)).toBeInTheDocument();
  });

  it("shows the evidence-coverage trust summary from real counts", () => {
    renderDashboard();
    expect(screen.getByText(/evidence coverage/i)).toBeInTheDocument();
    expect(screen.getByText(/screenplay facts/i)).toBeInTheDocument();
    expect(screen.getByText(/unknowns/i)).toBeInTheDocument();
  });

  it("links research evidence to impacted risks", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /research/i }));
    expect(screen.getAllByRole("heading", { name: /risk impact/i })).toHaveLength(2);
    expect(
      screen.getByRole("button", { name: /R-002.*harbor chase needs coordinator/i }),
    ).toBeInTheDocument();
  });

  it("summarizes the dependency graph from real data", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(screen.getByRole("tab", { name: /dependencies/i }));
    expect(screen.getByText(/risks? · \d+ scenes? · \d+ links/i)).toBeInTheDocument();
    expect(screen.getByText("Risk", { selector: "li" })).toBeInTheDocument();
  });
});

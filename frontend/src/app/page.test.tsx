import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "@/app/page";
import type { AnalyzeResponse, RunStatus } from "@/types";

const { mockPostAnalyze, mockPostPlan, mockGetRunStatus, mockRetryRun, mockExtract, mockGetDemo } =
  vi.hoisted(() => ({
    mockPostAnalyze: vi.fn(),
    mockPostPlan: vi.fn(),
    mockGetRunStatus: vi.fn(),
    mockRetryRun: vi.fn(),
    mockExtract: vi.fn(),
    mockGetDemo: vi.fn(),
  }));

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...mod,
    api: {
      getHealth: vi.fn().mockResolvedValue({ status: "ok", service: "t", version: "0" }),
      getStatus: vi.fn().mockResolvedValue({}),
      postAnalyze: mockPostAnalyze,
      postPlan: mockPostPlan,
      getRunStatus: mockGetRunStatus,
      retryRun: mockRetryRun,
      getDemoScreenplay: mockGetDemo,
      listProjects: vi.fn().mockResolvedValue([]),
      getProjectRuns: vi.fn().mockResolvedValue([]),
    },
  };
});

vi.mock("@/lib/screenplay", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/screenplay")>();
  return { ...mod, extractTextFromFile: mockExtract };
});

const fixture: AnalyzeResponse = {
  project_title: "Neon Harbor",
  run_id: "run-test123",
  analysis: {
    project_title: "Neon Harbor",
    genre: "action",
    estimated_complexity: "high",
    scenes: [],
    characters: ["Mara"],
    locations: ["Pier 9"],
    props: ["Lantern"],
    vehicles: [],
    brands: [],
    music: [],
    stunts: ["chase"],
    vfx_requirements: [],
    weather_dependencies: ["rain"],
    time_dependencies: [],
    production_dependencies: ["chase"],
    initial_concerns: [
      {
        title: "Night pier stunt",
        description: "Chase on a wet pier at night.",
        category: "stunt",
        scene_numbers: [2],
        evidence_level: "explicit",
        recommendation: "Add a safety day.",
      },
    ],
  },
  risks: [
    {
      id: "R-001",
      scene_number: 2,
      category: "stunt",
      severity: "high",
      title: "Harbor chase needs coordinator",
      description: "Night chase on wet pier.",
      why_it_matters: "Without a coordinator the shoot day cannot run.",
      evidence_items: [
        { kind: "screenplay", text: "A car chase erupts" },
        { kind: "inference", text: "Stunt keywords imply specialist personnel." },
      ],
      recommendation: "Hire coordinator and add safety day.",
      confidence: "high",
      status: "open",
    },
  ],
  recommendations: [
    {
      id: "REC-001",
      priority: 2,
      title: "Plan the harbor stunt",
      description: "Coordinator plus rehearsal day.",
      addresses_risk_ids: ["R-001"],
      expected_impact: "Removes the high penalty for R-001.",
      action_type: "plan_stunt",
    },
  ],
  readiness: {
    score: 87.5,
    status: "READY",
    critical_count: 0,
    high_count: 1,
    medium_count: 0,
    low_count: 0,
    total_risks: 1,
    blockers: ["R-001"],
    methodology: "score = 100 − Σpenalties",
  },
  research_notes: ["External research: not run (placeholder)."],
  readiness_score: 87.5,
  risk_counts: { critical: 0, high: 1, medium: 0, low: 0 },
};

function completedStatus(): RunStatus {
  return {
    run_id: "run-test123",
    project_id: "proj-1",
    status: "completed",
    current_stage: "completed",
    progress: 100,
    has_results: true,
    events: [
      {
        seq: 1,
        ts: "2026-09-09T14:32:08+00:00",
        type: "screenplay_parsed",
        message: "Screenplay parsed",
      },
    ],
    result: fixture,
  };
}

function txtFile() {
  return new File(["INT. PIER - NIGHT\nMara runs. ".repeat(20)], "script.txt", {
    type: "text/plain",
  });
}

async function uploadAndAnalyze(user: ReturnType<typeof userEvent.setup>) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  await user.upload(input, txtFile());
  await user.click(screen.getByRole("button", { name: /analyze production/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
  mockExtract.mockResolvedValue("INT. PIER - NIGHT\nMara runs. ".repeat(20));
  mockPostAnalyze.mockResolvedValue({
    run_id: "run-test123",
    project_id: "proj-1",
    status: "queued",
  });
  mockGetRunStatus.mockResolvedValue(completedStatus());
});

describe("CineGuard journey", () => {
  it("disables Analyze Production until a valid screenplay is selected", async () => {
    render(<Home />);
    const cta = screen.getByRole("button", { name: /analyze production/i });
    expect(cta).toBeDisabled();
  });

  it("shows upload validation for unsupported files", async () => {
    render(<Home />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const bad = new File(["x"], "virus.exe", { type: "application/octet-stream" });
    // fireEvent bypasses the input's accept filter (like drag & drop),
    // so component-level validation is exercised.
    fireEvent.change(input, { target: { files: [bad] } });
    expect(await screen.findByRole("alert")).toHaveTextContent(/unsupported file type/i);
    expect(screen.getByRole("button", { name: /analyze production/i })).toBeDisabled();
  });

  it("surfaces backend errors without fake success", async () => {
    const user = userEvent.setup();
    mockPostAnalyze.mockRejectedValueOnce(new Error("boom"));
    render(<Home />);
    await uploadAndAnalyze(user);
    expect(await screen.findByRole("alert")).toHaveTextContent(/boom|failed/i);
    expect(screen.queryByText(/production readiness/i)).not.toBeInTheDocument();
  });

  it("polls the run and renders real backend values (no hardcoded scores)", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await uploadAndAnalyze(user);
    await waitFor(() => expect(screen.getByText("87.5%")).toBeInTheDocument());
    expect(mockGetRunStatus).toHaveBeenCalledWith("run-test123");
    expect(screen.getByText(/harbor chase needs coordinator/i)).toBeInTheDocument();
    expect(screen.getByText(/hire coordinator/i)).toBeInTheDocument();
    expect(screen.getByText("Pier 9")).toBeInTheDocument();
    expect(screen.getByText(/night pier stunt/i)).toBeInTheDocument();
    // Fixture-driven, not the old 61% demo concept.
    expect(screen.queryByText("61%")).not.toBeInTheDocument();
  });

  it("shows live backend stage while tracking", async () => {
    const user = userEvent.setup();
    mockGetRunStatus
      .mockResolvedValueOnce({
        run_id: "run-test123",
        status: "researching",
        current_stage: "researching",
        progress: 40,
        has_results: false,
        events: [],
      })
      .mockResolvedValue(completedStatus());
    render(<Home />);
    await uploadAndAnalyze(user);
    expect(await screen.findByText(/stage: researching/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("87.5%")).toBeInTheDocument());
  });

  it("shows the failed stage with retry, then recovers", async () => {
    const user = userEvent.setup();
    mockGetRunStatus.mockResolvedValueOnce({
      run_id: "run-test123",
      status: "failed",
      current_stage: "reasoning_risks",
      progress: 65,
      has_results: false,
      events: [],
      error: { code: "GEMINI_ERROR", message: "Gemini request failed.", stage: "reasoning_risks" },
    });
    mockRetryRun.mockResolvedValueOnce({ run_id: "run-test123", status: "queued", attempt: 2 });
    render(<Home />);
    await uploadAndAnalyze(user);
    expect(await screen.findByText(/failed during reasoning risks/i)).toBeInTheDocument();
    expect(screen.getByText(/gemini request failed/i)).toBeInTheDocument();
    expect(screen.queryByText(/production readiness/i)).not.toBeInTheDocument();
    mockGetRunStatus.mockResolvedValue(completedStatus());
    await user.click(screen.getByRole("button", { name: /retry analysis/i }));
    expect(mockRetryRun).toHaveBeenCalledWith("run-test123");
    await waitFor(() => expect(screen.getByText("87.5%")).toBeInTheDocument());
  });

  it("renders readiness status, evidence labels and recommendations", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await uploadAndAnalyze(user);
    await waitFor(() => expect(screen.getByText("87.5%")).toBeInTheDocument());
    expect(document.querySelector(".readiness-label")).toHaveTextContent(/READY/);
    expect(screen.getByText("SCREENPLAY FACT")).toBeInTheDocument();
    expect(screen.getByText("INFERENCE", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText(/without a coordinator/i)).toBeInTheDocument();
    expect(screen.getByText(/plan the harbor stunt/i)).toBeInTheDocument();
  });

  it("builds a fix plan from selected recommendations", async () => {
    const user = userEvent.setup();
    mockPostPlan.mockResolvedValueOnce({
      project_title: "Neon Harbor",
      run_id: "run-test123",
      affected_risk_ids: ["R-001"],
      projected_readiness: {
        score: 95.0,
        status: "READY",
        critical_count: 0,
        high_count: 0,
        medium_count: 0,
        low_count: 0,
        total_risks: 1,
        blockers: [],
      },
      fix_plan: {
        actions: [
          {
            id: "ACT-001",
            recommendation_id: "REC-001",
            title: "Plan the harbor stunt",
            affected_scenes: [2],
            affected_risk_ids: ["R-001"],
            expected_risk_reduction: 5.0,
            schedule_impact: "Needs rehearsal day.",
          },
        ],
        affected_risk_ids: ["R-001"],
        projected_readiness: {
          score: 95.0,
          status: "READY",
          critical_count: 0,
          high_count: 0,
          medium_count: 0,
          low_count: 0,
          total_risks: 1,
          blockers: [],
        },
        remaining_blockers: [],
        schedule_impact: "1 action covering 1 risk.",
        revised_plan: "Execute and re-run analysis.",
      },
    });
    render(<Home />);
    await uploadAndAnalyze(user);
    await waitFor(() => expect(screen.getByText("87.5%")).toBeInTheDocument());
    const buildBtn = screen.getByRole("button", { name: /build revised production plan/i });
    expect(buildBtn).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /plan the harbor stunt/i }));
    expect(buildBtn).toBeEnabled();
    await user.click(buildBtn);
    await waitFor(() => expect(screen.getByText("95.0%")).toBeInTheDocument());
    expect(mockPostPlan).toHaveBeenCalledWith("run-test123", ["REC-001"]);
  });

  it("loads the demo production and analyzes it through the real pipeline", async () => {
    const user = userEvent.setup();
    mockGetDemo.mockResolvedValueOnce({
      title: "Neon Harbor (Demo Production)",
      screenplay_text: "INT. PIER - NIGHT\nMara runs. ".repeat(20),
      is_fictional: true,
      note: "Fictional demo input.",
    });
    render(<Home />);
    await user.click(screen.getByRole("button", { name: /load demo production/i }));
    expect(await screen.findByText(/demo input · fictional/i)).toBeInTheDocument();
    // Analyze is enabled with no file; the demo text goes through postAnalyze.
    const analyze = screen.getByRole("button", { name: /^analyze production$/i });
    expect(analyze).toBeEnabled();
    await user.click(analyze);
    expect(mockPostAnalyze).toHaveBeenCalledWith(
      expect.objectContaining({
        project_title: "Neon Harbor (Demo Production)",
        screenplay_text: expect.stringContaining("Mara runs"),
      }),
    );
    await waitFor(() => expect(screen.getByText("87.5%")).toBeInTheDocument());
  });

  it("shows a friendly error when the demo cannot load", async () => {
    const user = userEvent.setup();
    mockGetDemo.mockRejectedValueOnce(new Error("demo down"));
    render(<Home />);
    await user.click(screen.getByRole("button", { name: /load demo production/i }));
    expect(await screen.findByText(/demo down/i)).toBeInTheDocument();
  });
});

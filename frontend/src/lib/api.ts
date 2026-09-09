import { API_BASE_URL } from "@/lib/config";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  DemoScreenplay,
  HealthResponse,
  PlanResponse,
  Project,
  RunAccepted,
  RunStatus,
  RunSummary,
} from "@/types";

export type ApiErrorKind = "validation" | "backend" | "network";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  details?: unknown;

  constructor(kind: ApiErrorKind, message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.details = details;
  }
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function errorPayload(body: unknown): { code?: string; message?: string } | null {
  if (typeof body !== "object" || body === null) return null;
  const err = (body as { error?: unknown }).error;
  if (typeof err === "object" && err !== null) {
    const { code, message } = err as { code?: unknown; message?: unknown };
    return {
      code: typeof code === "string" ? code : undefined,
      message: typeof message === "string" ? message : undefined,
    };
  }
  return null;
}

function toError(res: Response, body: unknown): ApiError {
  const envelope = errorPayload(body);
  if (envelope?.message) {
    const kind = res.status === 422 ? "validation" : "backend";
    return new ApiError(kind, envelope.message, res.status, body);
  }
  // Legacy shapes (pre-envelope backends).
  if (res.status === 422) {
    return new ApiError(
      "validation",
      "The screenplay was rejected by the backend. Try a longer extract or check the file.",
      res.status,
      body,
    );
  }
  const msg =
    typeof body === "object" && body !== null && "message" in body
      ? String((body as { message: unknown }).message)
      : `Backend responded with status ${res.status}.`;
  return new ApiError("backend", msg, res.status, body);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      ...init,
    });
  } catch (err) {
    throw new ApiError(
      "network",
      `Cannot reach the backend at ${API_BASE_URL}. Is it running?`,
      undefined,
      err,
    );
  }
  if (!res.ok) {
    throw toError(res, await parseBody(res));
  }
  return (await res.json()) as T;
}

export const api = {
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },

  getStatus(): Promise<unknown> {
    return request<unknown>("/api/status");
  },

  postAnalyze(req: AnalyzeRequest): Promise<RunAccepted> {
    return request<RunAccepted>("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  },

  getRunStatus(run_id: string): Promise<RunStatus> {
    return request<RunStatus>(`/api/runs/${encodeURIComponent(run_id)}`);
  },

  retryRun(run_id: string): Promise<RunAccepted> {
    return request<RunAccepted>(`/api/runs/${encodeURIComponent(run_id)}/retry`, {
      method: "POST",
    });
  },

  listProjects(): Promise<Project[]> {
    return request<Project[]>("/api/projects");
  },

  getProjectRuns(project_id: string): Promise<RunSummary[]> {
    return request<RunSummary[]>(`/api/projects/${encodeURIComponent(project_id)}/runs`);
  },

  getDemoScreenplay(): Promise<DemoScreenplay> {
    return request<DemoScreenplay>("/api/demo/screenplay");
  },

  postPlan(run_id: string, selected_recommendation_ids: string[]): Promise<PlanResponse> {
    return request<PlanResponse>("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id, selected_recommendation_ids }),
    });
  },

  getRun(run_id: string): Promise<AnalyzeResponse> {
    return request<AnalyzeResponse>(`/api/runs/${encodeURIComponent(run_id)}`);
  },
};

export function friendlyErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong. Please try again.";
}

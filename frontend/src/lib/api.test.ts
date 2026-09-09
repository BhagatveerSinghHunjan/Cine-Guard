import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/lib/api";

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API error envelope", () => {
  it("surfaces the envelope message and code", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementation(() =>
          Promise.resolve(
            jsonResponse(
              { error: { code: "RUN_NOT_READY", message: "Not ready yet.", details: {} } },
              409,
            ),
          ),
        ),
    );
    await expect(api.getRunStatus("run-x")).rejects.toMatchObject({
      name: "ApiError",
      message: "Not ready yet.",
    } as Partial<ApiError>);
    try {
      await api.getRunStatus("run-x");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(409);
    }
  });

  it("keeps validation kind for 422 envelopes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(
            { error: { code: "VALIDATION_ERROR", message: "Bad input.", details: {} } },
            422,
          ),
        ),
    );
    try {
      await api.getRunStatus("run-x");
      expect.unreachable();
    } catch (err) {
      expect((err as ApiError).kind).toBe("validation");
      expect((err as ApiError).message).toBe("Bad input.");
    }
  });

  it("reports network failures without leaking the URL internals", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    await expect(api.getRunStatus("run-x")).rejects.toThrow(/cannot reach the backend/i);
  });
});

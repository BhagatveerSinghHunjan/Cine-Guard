import { describe, expect, it } from "vitest";
import { MAX_FILE_SIZE_BYTES, formatFileSize, validateScreenplayFile } from "@/lib/screenplay";

describe("validateScreenplayFile", () => {
  it("accepts pdf and txt", () => {
    expect(validateScreenplayFile({ name: "script.pdf", size: 1024 })).toEqual({ ok: true });
    expect(validateScreenplayFile({ name: "script.txt", size: 500 })).toEqual({ ok: true });
  });

  it("rejects unsupported extensions", () => {
    const r = validateScreenplayFile({ name: "malware.exe", size: 100 });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toMatch(/Unsupported file type/);
  });

  it("rejects empty and oversize files", () => {
    expect(validateScreenplayFile({ name: "a.pdf", size: 0 }).ok).toBe(false);
    const big = validateScreenplayFile({ name: "a.pdf", size: MAX_FILE_SIZE_BYTES + 1 });
    expect(big.ok).toBe(false);
  });
});

describe("formatFileSize", () => {
  it("formats bytes, kb, mb", () => {
    expect(formatFileSize(0)).toBe("0 B");
    expect(formatFileSize(2048)).toMatch(/KB/);
    expect(formatFileSize(5 * 1024 * 1024)).toMatch(/MB/);
  });
});

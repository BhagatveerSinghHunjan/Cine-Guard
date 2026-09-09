export const MAX_FILE_SIZE_BYTES = 12 * 1024 * 1024;

// Mirrors backend MAX_SCREENPLAY_CHARS — over-limit input is rejected with a
// clear error, never silently truncated.
export const MAX_SCREENPLAY_CHARS = 200_000;

export const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md", ".fountain"] as const;

export const ACCEPT_ATTRIBUTE = ".pdf,.txt,.md,.fountain,application/pdf,text/plain";

export class ScreenplayExtractionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ScreenplayExtractionError";
  }
}

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

export function validateScreenplayFile(file: {
  name: string;
  size: number;
  type?: string;
}): { ok: true } | { ok: false; error: string } {
  const ext = extensionOf(file.name);
  if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(ext)) {
    return {
      ok: false,
      error: `Unsupported file type “${ext || "unknown"}”. Please upload a PDF or plain-text screenplay (.pdf, .txt, .md).`,
    };
  }
  if (file.size <= 0) {
    return { ok: false, error: "That file looks empty. Please choose a file with content." };
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      ok: false,
      error: `File is ${formatFileSize(file.size)}. Maximum supported size is ${formatFileSize(MAX_FILE_SIZE_BYTES)}.`,
    };
  }
  return { ok: true };
}

async function extractPdfText(file: File): Promise<string> {
  // Dynamic import keeps pdfjs out of SSR / initial bundle.
  const pdfjs = await import("pdfjs-dist");
  const lib = pdfjs as unknown as {
    GlobalWorkerOptions: { workerSrc: string };
    getDocument: (opts: { data: ArrayBuffer }) => { promise: Promise<PdfDoc> };
  };
  interface PdfPage {
    getTextContent: () => Promise<{ items: Array<{ str?: string }> }>;
  }
  interface PdfDoc {
    numPages: number;
    getPage: (n: number) => Promise<PdfPage>;
  }
  if (!lib.GlobalWorkerOptions.workerSrc) {
    lib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.2.67/pdf.worker.min.mjs";
  }
  const data = await file.arrayBuffer();
  const doc = await lib.getDocument({ data }).promise;
  const pages = Math.min(doc.numPages, 200);
  const chunks: string[] = [];
  for (let n = 1; n <= pages; n++) {
    const page = await doc.getPage(n);
    const content = await page.getTextContent();
    const line = content.items.map((it) => (typeof it.str === "string" ? it.str : "")).join(" ");
    if (line.trim()) chunks.push(line);
  }
  return chunks.join("\n\n");
}

/** Read a File into screenplay text. Throws ScreenplayExtractionError with UI-safe copy. */
export async function extractTextFromFile(file: File): Promise<string> {
  const ext = extensionOf(file.name);
  let text: string;
  try {
    text = ext === ".pdf" ? await extractPdfText(file) : await file.text();
  } catch {
    throw new ScreenplayExtractionError(
      "Could not read that PDF in the browser. Try exporting it as plain text (.txt) and uploading again.",
    );
  }
  const cleaned = text.replace(/\r/g, "").trim();
  if (cleaned.length < 50) {
    throw new ScreenplayExtractionError(
      "Very little readable text was found in that file. Scanned-image PDFs are not supported yet — please upload a text-based PDF or .txt.",
    );
  }
  if (cleaned.length > MAX_SCREENPLAY_CHARS) {
    throw new ScreenplayExtractionError(
      `Extracted text is ${cleaned.length.toLocaleString()} characters; the limit is ${MAX_SCREENPLAY_CHARS.toLocaleString()}. Please upload a shorter extract — chunked screenplays are planned.`,
    );
  }
  return cleaned;
}

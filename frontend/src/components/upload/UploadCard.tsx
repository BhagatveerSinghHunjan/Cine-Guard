"use client";

import { useRef, useState } from "react";
import { ACCEPT_ATTRIBUTE, formatFileSize, validateScreenplayFile } from "@/lib/screenplay";

interface Props {
  file: File | null;
  error: string | null;
  disabled?: boolean;
  onSelect: (file: File) => void;
  onError: (message: string) => void;
  onRemove: () => void;
}

export function UploadCard({ file, error, disabled, onSelect, onError, onRemove }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const describedBy = error ? "upload-error" : "upload-hint";

  function handleFile(candidate: File | undefined) {
    if (!candidate || disabled) return;
    const check = validateScreenplayFile(candidate);
    if (!check.ok) {
      onError(check.error);
      return;
    }
    onSelect(candidate);
  }

  return (
    <div
      className={`upload${dragging ? " upload-dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFile(e.dataTransfer.files?.[0]);
      }}
    >
      <div className="upload-head">
        <h2 id="upload-title" className="card-title">
          Screenplay
        </h2>
        <span className="upload-formats">PDF · TXT · MD</span>
      </div>

      {!file ? (
        <>
          <p id="upload-hint" className="muted">
            Drag &amp; drop your screenplay here, or browse your files. Text is extracted in your
            browser and sent to the backend for analysis.
          </p>
          <div className="upload-actions">
            <button
              type="button"
              className="btn btn-ghost"
              disabled={disabled}
              onClick={() => inputRef.current?.click()}
              aria-describedby={describedBy}
            >
              Browse files
            </button>
          </div>
        </>
      ) : (
        <div className="file-row">
          <div>
            <p className="file-name">{file.name}</p>
            <p className="muted">{formatFileSize(file.size)}</p>
          </div>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={disabled}
            onClick={onRemove}
            aria-label={`Remove ${file.name}`}
          >
            Remove
          </button>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        className="sr-only-file"
        accept={ACCEPT_ATTRIBUTE}
        aria-labelledby="upload-title"
        aria-describedby={describedBy}
        disabled={disabled}
        tabIndex={file ? -1 : 0}
        onChange={(e) => {
          handleFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {error ? (
        <p id="upload-error" className="field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

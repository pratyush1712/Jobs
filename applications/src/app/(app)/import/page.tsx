"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Loader,
  Trash2,
} from "lucide-react";
import { cn, pluralize } from "@/lib/utils";
import { parseFiles } from "@/lib/import/parse";
import { importRecords } from "@/lib/import/normalize";
import { PageHeader } from "@/components/shell/PageHeader";
import type { ImportedJobFields } from "@/types";
import type { ImportResult } from "@/lib/import/normalize";

type ImportPhase = "idle" | "previewing" | "importing" | "done" | "error";

interface PreviewData {
  records: ImportedJobFields[];
  parseErrors: string[];
  filenames: string[];
}

export default function ImportPage() {
  const [phase, setPhase] = useState<ImportPhase>("idle");
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [dragError, setDragError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    setDragError(null);
    setPhase("previewing");

    const parsed = await parseFiles(acceptedFiles);
    setPreview({
      records: parsed.records,
      parseErrors: parsed.errors,
      filenames: parsed.filenames,
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/json": [".json"],
      "application/x-ndjson": [".jsonl"],
      "text/plain": [".jsonl", ".json"],
    },
    multiple: true,
    onDropRejected: () => {
      setDragError("Only .json and .jsonl files are supported.");
    },
  });

  async function handleImport() {
    if (!preview) return;
    setPhase("importing");
    try {
      const res = await importRecords(
        preview.records,
        preview.filenames,
        preview.parseErrors,
      );
      setResult(res);
      setPhase("done");
    } catch (e) {
      setDragError(e instanceof Error ? e.message : "Import failed.");
      setPhase("error");
    }
  }

  function handleReset() {
    setPhase("idle");
    setPreview(null);
    setResult(null);
    setDragError(null);
  }

  return (
    <div className="flex-1 flex flex-col overflow-auto">
      <PageHeader title="Import" description="JSON / JSONL job postings" />

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-2xl mx-auto space-y-5">
          {/* Drop zone */}
          {phase === "idle" && (
            <div
              {...getRootProps()}
              className={cn(
                "relative flex flex-col items-center justify-center gap-4 px-8 py-14",
                "border-2 border-dashed rounded-xl cursor-pointer",
                "transition-colors",
                isDragActive
                  ? "border-violet bg-violet-muted"
                  : "border-divider hover:border-violet/40 hover:bg-surface-2",
              )}
            >
              <input {...getInputProps()} />
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-violet-muted">
                <Upload className="h-5 w-5 text-violet" />
              </div>
              <div className="text-center">
                <p className="text-[14px] font-medium text-text-primary">
                  {isDragActive
                    ? "Drop files here…"
                    : "Drop JSON or JSONL files here"}
                </p>
                <p className="text-[12px] text-text-tertiary mt-1">
                  or click to browse · supports .json and .jsonl
                </p>
              </div>
              {dragError && (
                <p className="text-[12px] text-rose-400">{dragError}</p>
              )}
            </div>
          )}

          {/* Preview */}
          {phase === "previewing" && preview && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-[14px] font-semibold text-text-primary">
                    Import Preview
                  </h2>
                  <p className="text-[12px] text-text-tertiary mt-0.5">
                    {pluralize(preview.records.length, "record")} from{" "}
                    {preview.filenames.join(", ")}
                  </p>
                </div>
                <button
                  onClick={handleReset}
                  className="text-[12px] text-text-tertiary hover:text-text-primary transition-colors flex items-center gap-1"
                >
                  <Trash2 className="h-3 w-3" />
                  Clear
                </button>
              </div>

              {/* Parse errors */}
              {preview.parseErrors.length > 0 && (
                <div className="flex items-start gap-2 px-3 py-3 rounded-lg bg-amber-950/30 border border-amber-800/30">
                  <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[12px] font-medium text-amber-300 mb-1">
                      {pluralize(preview.parseErrors.length, "parse error")}
                    </p>
                    <ul className="space-y-0.5">
                      {preview.parseErrors.slice(0, 5).map((e, i) => (
                        <li key={i} className="text-[11px] text-amber-400/80">
                          {e}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Record preview table */}
              <div className="bg-surface-2 border border-divider rounded-lg overflow-hidden">
                <div className="px-4 py-2.5 border-b border-divider flex items-center justify-between">
                  <span className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
                    Records to import
                  </span>
                  <span className="text-[11px] text-text-tertiary">
                    {preview.records.length} total
                  </span>
                </div>
                <div className="overflow-auto max-h-[340px]">
                  {preview.records.map((rec, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-4 py-2.5 border-b border-divider last:border-0 hover:bg-surface-3 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium text-text-primary truncate">
                          {rec.job_title ?? "Untitled"}
                        </p>
                        <p className="text-[11px] text-text-tertiary truncate mt-0.5">
                          {rec.company ?? "Unknown"}
                          {rec.location ? ` · ${rec.location}` : ""}
                          {rec.compensation ? ` · ${rec.compensation}` : ""}
                        </p>
                      </div>
                      {rec.confidence && (
                        <span
                          className={cn(
                            "text-[10px] px-1.5 py-0.5 rounded",
                            rec.confidence === "high"
                              ? "bg-violet-muted text-violet"
                              : rec.confidence === "medium"
                                ? "bg-amber-950/40 text-amber-300"
                                : "bg-rose-950/40 text-rose-300",
                          )}
                        >
                          {rec.confidence}
                        </span>
                      )}
                      {rec.seniority && rec.seniority !== "null" && (
                        <span className="text-[11px] text-text-tertiary shrink-0">
                          {rec.seniority}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Import button */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleImport}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2.5 rounded-lg",
                    "text-[13px] font-medium",
                    "bg-violet text-white",
                    "hover:opacity-90 transition-opacity",
                    preview.records.length === 0 &&
                      "opacity-50 cursor-not-allowed",
                  )}
                  disabled={preview.records.length === 0}
                >
                  <Upload className="h-4 w-4" />
                  Import {preview.records.length} records
                </button>
                <button
                  onClick={handleReset}
                  className="text-[13px] text-text-tertiary hover:text-text-secondary transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Loading */}
          {phase === "importing" && (
            <div className="flex flex-col items-center justify-center gap-4 py-16">
              <Loader className="h-8 w-8 text-violet animate-spin" />
              <p className="text-[13px] text-text-secondary">
                Importing records…
              </p>
            </div>
          )}

          {/* Done */}
          {phase === "done" && result && (
            <div className="space-y-4">
              <div className="flex items-start gap-3 px-4 py-4 rounded-lg bg-emerald-950/30 border border-emerald-800/30">
                <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-[14px] font-semibold text-emerald-300">
                    Import complete
                  </p>
                  <p className="text-[12px] text-emerald-400/70 mt-1">
                    {result.inserted} new records added · {result.skipped}{" "}
                    duplicates skipped
                  </p>
                </div>
              </div>

              {result.errors.length > 0 && (
                <div className="flex items-start gap-2 px-3 py-3 rounded-lg bg-rose-950/30 border border-rose-800/30">
                  <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[12px] font-medium text-rose-300 mb-1">
                      {pluralize(result.errors.length, "error")} during import
                    </p>
                    <ul className="space-y-0.5">
                      {result.errors.slice(0, 5).map((e, i) => (
                        <li key={i} className="text-[11px] text-rose-400/80">
                          {e}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3">
                <Link
                  href="/jobs"
                  className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[13px] font-medium bg-violet text-white hover:opacity-90 transition-opacity"
                >
                  View jobs
                </Link>
                <button
                  onClick={handleReset}
                  className="text-[13px] text-text-tertiary hover:text-text-secondary transition-colors"
                >
                  Import more
                </button>
              </div>
            </div>
          )}

          {/* Error */}
          {phase === "error" && (
            <div className="flex items-start gap-3 px-4 py-4 rounded-lg bg-rose-950/30 border border-rose-800/30">
              <XCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-[14px] font-semibold text-rose-300">
                  Import failed
                </p>
                {dragError && (
                  <p className="text-[12px] text-rose-400/70 mt-1">
                    {dragError}
                  </p>
                )}
                <button
                  onClick={handleReset}
                  className="mt-3 text-[12px] text-rose-400 hover:underline"
                >
                  Try again
                </button>
              </div>
            </div>
          )}

          {/* Info box */}
          {phase === "idle" && (
            <div className="bg-surface-2 border border-divider rounded-lg p-4 space-y-3">
              <h3 className="text-[12px] font-semibold text-text-secondary uppercase tracking-wider">
                Expected Format
              </h3>
              <div className="space-y-1.5">
                <FormatRow
                  icon={FileText}
                  label=".jsonl"
                  desc="One JSON object per line (Welcome to the Jungle export format)"
                />
                <FormatRow
                  icon={FileText}
                  label=".json"
                  desc="A single JSON object or an array of objects"
                />
              </div>
              <div className="pt-1 border-t border-divider">
                <p className="text-[11px] text-text-tertiary leading-relaxed">
                  Records are deduplicated by job URL (or company + title +
                  location). Duplicate records are skipped automatically.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FormatRow({
  icon: Icon,
  label,
  desc,
}: {
  icon: React.ElementType;
  label: string;
  desc: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon className="h-3.5 w-3.5 text-violet mt-0.5 shrink-0" />
      <div>
        <span className="text-[12px] font-medium text-text-secondary font-mono">
          {label}
        </span>
        <span className="text-[12px] text-text-tertiary ml-2">{desc}</span>
      </div>
    </div>
  );
}

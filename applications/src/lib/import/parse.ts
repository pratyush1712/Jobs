/**
 * Client-side file parsing for JSON and JSONL formats.
 * All parsing happens in-browser — no network requests.
 */

import type { ImportedJobFields } from "@/types";

export interface ParseResult {
  records: ImportedJobFields[];
  errors: string[];
  format: "json" | "jsonl" | "unknown";
}

/**
 * Parses a File object into raw job field records.
 * Supports both .json (array or single object) and .jsonl (newline-delimited JSON).
 */
export async function parseFile(file: File): Promise<ParseResult> {
  const text = await file.text();
  const trimmed = text.trim();

  if (!trimmed) {
    return { records: [], errors: ["File is empty."], format: "unknown" };
  }

  // Detect format by extension or content structure
  const isJsonl =
    file.name.endsWith(".jsonl") ||
    (!trimmed.startsWith("[") && !trimmed.startsWith("{"));

  if (isJsonl || file.name.endsWith(".jsonl")) {
    return parseJsonl(trimmed);
  }

  return parseJson(trimmed);
}

/**
 * Parses a newline-delimited JSON string.
 * Each non-empty line is parsed independently so partial errors don't fail the batch.
 */
function parseJsonl(text: string): ParseResult {
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  const records: ImportedJobFields[] = [];
  const errors: string[] = [];

  lines.forEach((line, i) => {
    try {
      const parsed = JSON.parse(line) as Record<string, unknown>;
      records.push(parsed as ImportedJobFields);
    } catch (e) {
      errors.push(
        `Line ${i + 1}: ${e instanceof Error ? e.message : "Parse error"}`,
      );
    }
  });

  return { records, errors, format: "jsonl" };
}

/**
 * Parses a JSON string that may be an array or a single object.
 */
function parseJson(text: string): ParseResult {
  const errors: string[] = [];

  try {
    const parsed = JSON.parse(text) as unknown;

    if (Array.isArray(parsed)) {
      const records = parsed.map((item) => item as ImportedJobFields);
      return { records, errors, format: "json" };
    }

    if (typeof parsed === "object" && parsed !== null) {
      return {
        records: [parsed as ImportedJobFields],
        errors,
        format: "json",
      };
    }

    return {
      records: [],
      errors: ["Expected a JSON object or array."],
      format: "json",
    };
  } catch (e) {
    return {
      records: [],
      errors: [e instanceof Error ? e.message : "JSON parse error"],
      format: "json",
    };
  }
}

/**
 * Parses multiple files and merges results.
 */
export async function parseFiles(
  files: File[],
): Promise<ParseResult & { filenames: string[] }> {
  const allRecords: ImportedJobFields[] = [];
  const allErrors: string[] = [];
  const filenames: string[] = [];
  let format: ParseResult["format"] = "unknown";

  for (const file of files) {
    const result = await parseFile(file);
    allRecords.push(...result.records);
    allErrors.push(...result.errors.map((e) => `[${file.name}] ${e}`));
    filenames.push(file.name);
    if (result.format !== "unknown") {
      format = result.format;
    }
  }

  return { records: allRecords, errors: allErrors, format, filenames };
}

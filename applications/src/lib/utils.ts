import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format, parseISO, isValid } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Returns a relative time string like "3 days ago" or "just now".
 */
export function timeAgo(dateStr?: string): string {
  if (!dateStr) return "—";
  try {
    const date = parseISO(dateStr);
    if (!isValid(date)) return "—";
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return "—";
  }
}

/**
 * Formats a date string as "Apr 28, 2026".
 */
export function formatDate(dateStr?: string): string {
  if (!dateStr) return "—";
  try {
    const date = parseISO(dateStr);
    if (!isValid(date)) return "—";
    return format(date, "MMM d, yyyy");
  } catch {
    return "—";
  }
}

/**
 * Formats a date as "YYYY-MM-DD" for input[type=date].
 */
export function formatDateInput(dateStr?: string): string {
  if (!dateStr) return "";
  try {
    const date = parseISO(dateStr);
    if (!isValid(date)) return "";
    return format(date, "yyyy-MM-dd");
  } catch {
    return "";
  }
}

/**
 * Truncates a string with ellipsis after maxLen characters.
 */
export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return `${str.slice(0, maxLen)}…`;
}

/**
 * Strips http/https and trailing slash from a URL for display.
 */
export function displayUrl(url?: string): string {
  if (!url) return "";
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

/**
 * Returns initials for a company name (up to 2 chars).
 */
export function companyInitials(company?: string): string {
  if (!company) return "?";
  const words = company.trim().split(/\s+/);
  if (words.length === 1) {
    return (words[0]?.slice(0, 2) ?? "?").toUpperCase();
  }
  return ((words[0]?.[0] ?? "") + (words[1]?.[0] ?? "")).toUpperCase();
}

/**
 * Groups an array of items by a key extractor.
 */
export function groupBy<T>(
  items: T[],
  keyFn: (item: T) => string,
): Record<string, T[]> {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const key = keyFn(item);
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
}

/**
 * Counts occurrences of each key in an array.
 */
export function countBy<T>(
  items: T[],
  keyFn: (item: T) => string,
): Record<string, number> {
  return items.reduce<Record<string, number>>((acc, item) => {
    const key = keyFn(item);
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}

/**
 * Returns top N entries from a Record<string, number> sorted by count desc.
 */
export function topN(
  counts: Record<string, number>,
  n: number,
): Array<{ label: string; count: number }> {
  return Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, n)
    .map(([label, count]) => ({ label, count }));
}

/**
 * Pluralizes a word based on count.
 */
export function pluralize(
  count: number,
  word: string,
  plural?: string,
): string {
  if (count === 1) return `1 ${word}`;
  return `${count} ${plural ?? `${word}s`}`;
}

/**
 * Phrases produced by the LLM (or the fetch layer) that signal the
 * enrichment did not actually extract job content.
 */
const ENRICHMENT_FAILURE_PREFIXES = [
  "the fetched page does not contain",
  "the page does not contain",
  "this page does not contain",
  "no job",
  "page_fetch_error",
] as const;

/**
 * Returns the enrichment status of a job record:
 * - "enriched" — summary exists and is not an error/failure message
 * - "failed"   — enrichment ran but produced an error or a "no content" LLM response
 * - "none"     — enrichment has not been run yet (empty summary, no error stored)
 */
export function getEnrichmentStatus(job: {
  summary?: string;
  confidence?: string;
  raw?: Record<string, unknown>;
  raw_listing?: Record<string, unknown>;
}): "enriched" | "failed" | "none" {
  const raw = (job.raw ?? job.raw_listing) as
    | Record<string, unknown>
    | undefined;
  if (raw?.enrichment_error) return "failed";

  const summary = (job.summary ?? "").trim().toLowerCase();

  if (
    summary &&
    ENRICHMENT_FAILURE_PREFIXES.some((p) => summary.startsWith(p))
  ) {
    return "failed";
  }

  // "low" confidence with no summary means the LLM returned an empty extraction.
  if (job.confidence === "low" && !summary) return "failed";

  if (summary.length > 20) return "enriched";

  return "none";
}

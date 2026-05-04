/**
 * Normalizes and deduplicates raw parsed job records into full JobRecord objects.
 * Also handles inserting/updating them in the Dexie database.
 */

import { v4 as uuidv4 } from "uuid";
import type {
  ImportedJobFields,
  JobRecord,
  ActivityItem,
  ImportBatch,
  ApplicationStatus,
  Seniority,
} from "@/types";
import { getDb } from "@/lib/db";

/** Generates a stable dedupe key from job data. */
export function buildDedupeKey(fields: ImportedJobFields): string {
  if (fields.job_url && fields.job_url.length > 0) {
    // Strip token query params for better deduplication
    try {
      const url = new URL(fields.job_url);
      url.search = "";
      return url.toString();
    } catch {
      return fields.job_url;
    }
  }

  const company = (fields.company ?? "").toLowerCase().trim();
  const title = (fields.job_title ?? "").toLowerCase().trim();
  const location = (fields.location ?? "").toLowerCase().trim();
  return `${company}::${title}::${location}`;
}

/**
 * Maps snake_case seniority values from the extraction pipeline to the
 * title-case values used by the app's SENIORITY_LEVELS constants and filters.
 */
const SENIORITY_MAP: Record<string, Seniority> = {
  new_grad: "New Grad",
  entry_level: "Entry Level",
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  staff: "Staff",
  principal: "Principal",
  internship: "Internship",
};

/** Normalizes a seniority value from the pipeline to a Seniority type. */
function normalizeSeniority(val: unknown): Seniority | string {
  if (typeof val !== "string" || val.length === 0) return "";
  const key = val.toLowerCase().replace(/[\s-]+/g, "_");
  return SENIORITY_MAP[key] ?? val;
}

/** Set of all valid ApplicationStatus values for O(1) lookup. */
const VALID_APPLICATION_STATUSES = new Set<ApplicationStatus>([
  "interested",
  "saved",
  "applied",
  "oa",
  "recruiter_screen",
  "interview",
  "final_round",
  "offer",
  "rejected",
  "archived",
]);

/**
 * Validates and returns a typed ApplicationStatus.
 * Falls back to "interested" for unknown or missing values.
 */
function normalizeApplicationStatus(val: unknown): ApplicationStatus {
  if (
    typeof val === "string" &&
    VALID_APPLICATION_STATUSES.has(val as ApplicationStatus)
  ) {
    return val as ApplicationStatus;
  }
  return "interested";
}

/** Normalizes a single raw record into a JobRecord. */
export function normalizeRecord(
  fields: ImportedJobFields,
  batchId: string,
): Omit<JobRecord, "id"> {
  const now = new Date().toISOString();
  const dedupeKey = buildDedupeKey(fields);

  // Resolve alias fields: the extraction pipeline uses different field names
  // for some values than the app schema expects.
  const subject = fields.subject ?? fields.email_subject;
  const visaSponsor =
    fields.visa_sponsorship ?? fields.visa_sponsorship_policy ?? "";
  const rawData = fields.raw ?? fields.raw_listing;

  // Carry over pre-filled tracking state from the pipeline when available.
  const applicationStatus = normalizeApplicationStatus(
    fields.application_status,
  );
  // active === false means the listing has been deactivated; treat as archived.
  const archived = fields.active === false;

  const importActivity: ActivityItem = {
    id: uuidv4(),
    timestamp: now,
    text: "Job imported from file",
    kind: "import",
  };

  return {
    // Imported fields
    gmail_link: fields.gmail_link,
    message_id_header: fields.message_id_header,
    gmail_internal_id: fields.gmail_internal_id,
    thread_id: fields.thread_id,
    email_date: fields.email_date,
    sender: fields.sender,
    subject,
    job_url: fields.job_url,
    page_title: fields.page_title,
    company: fields.company ?? "",
    job_title: fields.job_title ?? "",
    location: fields.location ?? "",
    remote_policy: fields.remote_policy ?? "",
    employment_type: fields.employment_type ?? "",
    seniority: normalizeSeniority(fields.seniority),
    compensation: fields.compensation ?? "",
    visa_sponsorship: visaSponsor,
    summary: fields.summary ?? "",
    keywords: normalizeStringArray(fields.keywords),
    required_skills: normalizeStringArray(fields.required_skills),
    preferred_skills: normalizeStringArray(fields.preferred_skills),
    responsibilities: normalizeStringArray(fields.responsibilities),
    requirements: normalizeStringArray(fields.requirements),
    nice_to_have: normalizeStringArray(fields.nice_to_have),
    confidence: normalizeConfidence(fields.confidence),
    // Preserve extra pipeline metadata inside raw so the detail view can
    // surface it without requiring schema changes.
    raw: rawData,

    // Additional pipeline metadata fields carried into ImportedJobFields
    source: fields.source,
    company_url: fields.company_url,
    wttj_dashboard_url: fields.wttj_dashboard_url,
    locations: normalizeStringArray(fields.locations),
    date_posted_raw: fields.date_posted_raw,
    date_posted_human: fields.date_posted_human,
    faang_plus: fields.faang_plus ?? false,
    simplify_url: fields.simplify_url,

    // App-managed fields — carry over pre-filled values from the pipeline
    applicationStatus,
    saved: false,
    archived,
    dateApplied: fields.date_applied ?? undefined,
    referral: fields.referral ?? undefined,
    contactName: fields.contact_name ?? undefined,
    contactEmail: fields.contact_email ?? undefined,
    notes: fields.notes ?? undefined,
    nextFollowUpDate: fields.next_follow_up_date ?? undefined,
    salaryExpectation: fields.salary_expectation ?? undefined,
    activityLog: [importActivity],

    // Metadata
    dedupeKey,
    importedAt: now,
    createdAt: now,
    updatedAt: now,
    importBatchId: batchId,
  };
}

function normalizeStringArray(val: unknown): string[] {
  if (!val) return [];
  if (Array.isArray(val)) {
    return val
      .map((item) => (typeof item === "string" ? item.trim() : String(item)))
      .filter((s) => s.length > 0);
  }
  if (typeof val === "string" && val.trim().length > 0) {
    return [val.trim()];
  }
  return [];
}

function normalizeConfidence(val: unknown): "high" | "medium" | "low" {
  if (val === "high" || val === "medium" || val === "low") return val;
  return "medium";
}

/** Result of an import operation. */
export interface ImportResult {
  inserted: number;
  skipped: number;
  batchId: string;
  errors: string[];
}

/**
 * Normalizes records and inserts them into IndexedDB.
 * Deduplicates against existing records using dedupeKey.
 * Returns insert/skip counts and saves an ImportBatch record.
 */
export async function importRecords(
  rawRecords: ImportedJobFields[],
  sources: string[],
  parseErrors: string[] = [],
): Promise<ImportResult> {
  const db = getDb();
  const batchId = uuidv4();
  const now = new Date().toISOString();
  const errors = [...parseErrors];

  let inserted = 0;
  let skipped = 0;

  for (const raw of rawRecords) {
    try {
      const normalized = normalizeRecord(raw, batchId);

      // Check if this dedupeKey already exists
      const existing = await db.jobs
        .where("dedupeKey")
        .equals(normalized.dedupeKey)
        .first();

      if (existing) {
        skipped++;
        continue;
      }

      await db.jobs.add(normalized);
      inserted++;
    } catch (e) {
      errors.push(
        `Failed to insert record: ${e instanceof Error ? e.message : String(e)}`,
      );
    }
  }

  // Persist batch metadata
  const batch: Omit<ImportBatch, "id"> = {
    batchId,
    importedAt: now,
    sources,
    totalParsed: rawRecords.length,
    inserted,
    skipped,
  };

  await db.importBatches.add(batch);

  return { inserted, skipped, batchId, errors };
}

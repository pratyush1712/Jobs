/** Core domain types for the job tracker dashboard. */

export type ApplicationStatus =
  | "interested"
  | "saved"
  | "applied"
  | "oa"
  | "recruiter_screen"
  | "interview"
  | "final_round"
  | "offer"
  | "rejected"
  | "archived";

export type Confidence = "high" | "medium" | "low";

export type RemotePolicy = "remote" | "hybrid" | "onsite" | "flexible" | "";

export type EmploymentType =
  | "Full-Time"
  | "Part-Time"
  | "Contract"
  | "Internship"
  | "null"
  | "";

export type Seniority =
  | "Junior"
  | "Mid"
  | "Senior"
  | "Staff"
  | "Principal"
  | "New Grad"
  | "Entry Level"
  | "Internship"
  | "";

/** A single entry in the activity log for a job. */
export interface ActivityItem {
  /** Unique id for this log entry. */
  id: string;
  /** ISO timestamp. */
  timestamp: string;
  /** Human-readable description. */
  text: string;
  /** Optional old status when this was a status change. */
  fromStatus?: ApplicationStatus;
  /** New status when this was a status change. */
  toStatus?: ApplicationStatus;
  /** "note" | "status_change" | "import" | "edit" */
  kind: "note" | "status_change" | "import" | "edit";
}

/** Imported fields from the JSONL email extraction pipeline. */
export interface ImportedJobFields {
  /** Standard app field name for email subject. */
  subject?: string;
  gmail_link?: string;
  message_id_header?: string;
  gmail_internal_id?: string;
  thread_id?: string;
  email_date?: string;
  sender?: string;
  job_url?: string;
  page_title?: string;
  company?: string;
  job_title?: string;
  location?: string;
  remote_policy?: string;
  employment_type?: EmploymentType | string;
  seniority?: Seniority | string;
  compensation?: string;
  /** Standard app field name for visa sponsorship info. */
  visa_sponsorship?: string | null;
  summary?: string;
  keywords?: string[];
  required_skills?: string[];
  preferred_skills?: string[];
  responsibilities?: string[];
  requirements?: string[];
  nice_to_have?: string[];
  confidence?: Confidence | string;
  /** Raw original object for debugging. */
  raw?: Record<string, unknown>;

  /**
   * Extraction pipeline alias fields — field names differ from the app schema.
   * normalizeRecord maps these to the canonical fields above.
   */

  /** Alias for subject — wttj_gmail records use email_subject. */
  email_subject?: string;
  /** Alias for visa_sponsorship — simplify_github records use visa_sponsorship_policy. */
  visa_sponsorship_policy?: string;
  /** Alias for raw — pipeline records use raw_listing. */
  raw_listing?: Record<string, unknown>;

  /**
   * Pre-filled tracking state from the extraction pipeline.
   * normalizeRecord carries these into ApplicationFields when present.
   */

  /** Application status pre-filled by the pipeline (e.g. "interested", "applied"). */
  application_status?: string;
  /** ISO date string for when the application was submitted. */
  date_applied?: string;
  /** Referral source pre-filled by the pipeline. */
  referral?: string;
  /** Contact name pre-filled by the pipeline. */
  contact_name?: string;
  /** Contact email pre-filled by the pipeline. */
  contact_email?: string;
  /** Any notes pre-filled by the pipeline. */
  notes?: string;
  /** ISO date string for the next follow-up action. */
  next_follow_up_date?: string;
  /** Salary expectation string pre-filled by the pipeline. */
  salary_expectation?: string;
  /** Whether the listing is still active. Maps to !archived. */
  active?: boolean;

  /**
   * Additional metadata from the extraction pipeline preserved for reference.
   */

  /** Which pipeline produced this record ("simplify_github", "wttj_gmail", etc.). */
  source?: string;
  /** URL to the company page on the job board. */
  company_url?: string;
  /** URL to the WTTJ dashboard job entry. */
  wttj_dashboard_url?: string;
  /** Array of location strings (before flattening to a single location string). */
  locations?: string[];
  /** Raw date-posted value as returned by the source (may be a Unix timestamp string). */
  date_posted_raw?: string;
  /** ISO date string for when the job was posted. */
  date_posted_human?: string;
  /** Whether the company is considered FAANG+. */
  faang_plus?: boolean;
  /** Simplify.jobs source URL for GitHub-sourced records. */
  simplify_url?: string;
}

/** Application-managed fields tracked per job. */
export interface ApplicationFields {
  applicationStatus: ApplicationStatus;
  saved: boolean;
  archived: boolean;
  dateApplied?: string;
  notes?: string;
  nextFollowUpDate?: string;
  referral?: string;
  contactName?: string;
  contactEmail?: string;
  salaryExpectation?: string;
  activityLog: ActivityItem[];
}

/** The full persisted job record stored in IndexedDB. */
export interface JobRecord extends ImportedJobFields, ApplicationFields {
  /** Auto-assigned uuid by Dexie. */
  id?: number;
  /** Stable dedupe key: job_url or `${company}::${job_title}::${location}`. */
  dedupeKey: string;
  /** When this record was first imported. */
  importedAt: string;
  /** When first created in the DB. */
  createdAt: string;
  /** When last modified. */
  updatedAt: string;
  /** Which import batch this belongs to. */
  importBatchId?: string;
}

/** Metadata for a single import operation. */
export interface ImportBatch {
  /** Auto-assigned uuid by Dexie. */
  id?: number;
  /** Unique batch id. */
  batchId: string;
  /** ISO timestamp. */
  importedAt: string;
  /** Original filename(s). */
  sources: string[];
  /** Number of records in this batch. */
  totalParsed: number;
  /** Number of new records actually inserted. */
  inserted: number;
  /** Number skipped as duplicates. */
  skipped: number;
  /** Summary of statuses encountered. */
  summary?: Record<string, number>;
}

/** App settings stored in IndexedDB. */
export interface AppSettings {
  id?: number;
  key: string;
  value: unknown;
}

/* ── UI-only helper types ──────────────────────────────────────── */

export interface JobFilters {
  query: string;
  statuses: ApplicationStatus[];
  /** Pipeline source chips — "wttj_gmail" and/or "simplify_github". */
  source: string[];
  remotePolicy: string[];
  employmentType: string[];
  seniority: string[];
  confidence: string[];
  /**
   * true  = only jobs that were successfully enriched (non-empty summary, no error)
   * false = only jobs whose enrichment failed or that were never enriched
   * null  = no filter (show all)
   */
  enriched: boolean | null;
  saved: boolean | null;
  archived: boolean | null;
}

export type SortField =
  | "importedAt"
  | "dateApplied"
  | "company"
  | "job_title"
  | "email_date"
  | "confidence";

export type SortDirection = "asc" | "desc";

export interface SortState {
  field: SortField;
  direction: SortDirection;
}

export type ViewMode = "table" | "split";

/** Derived KPI metrics for the dashboard. */
export interface PipelineMetrics {
  total: number;
  saved: number;
  applied: number;
  interviewing: number;
  rejected: number;
  offers: number;
  archived: number;
}

/** Aggregated count per status for charting. */
export interface StatusCount {
  status: ApplicationStatus;
  label: string;
  count: number;
  color: string;
}

/** Count per date (YYYY-MM-DD) for time-series charts. */
export interface DateCount {
  date: string;
  count: number;
}

/** Count per string label for bar charts. */
export interface LabelCount {
  label: string;
  count: number;
}

"use client";

import { use } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { v4 as uuidv4 } from "uuid";
import {
  ArrowLeft,
  ExternalLink,
  Mail,
  Bookmark,
  BookmarkCheck,
  Calendar,
  CheckCircle,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";

import { db } from "@/lib/db";
import { STATUS_META, ALL_STATUSES } from "@/lib/constants";
import { cn, formatDate, timeAgo, companyInitials } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SkillBadge } from "@/components/ui/SkillBadge";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import type { ApplicationStatus, ActivityItem, JobRecord } from "@/types";

/* ── Zod schema for the tracking form ──────────────────────────── */
const trackingSchema = z.object({
  applicationStatus: z.string(),
  dateApplied: z.string().optional(),
  nextFollowUpDate: z.string().optional(),
  referral: z.string().optional(),
  contactName: z.string().optional(),
  contactEmail: z.string().optional(),
  salaryExpectation: z.string().optional(),
  notes: z.string().optional(),
});

type TrackingForm = z.infer<typeof trackingSchema>;

/* ── Page ────────────────────────────────────────────────────────── */
export default function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();

  const job = useLiveQuery(() => db.jobs.get(parseInt(id, 10)), [id]);

  if (job === undefined) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="h-5 w-5 rounded-full border-2 border-violet border-t-transparent animate-spin" />
      </div>
    );
  }

  if (job === null) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <p className="text-[14px] text-text-secondary">Job not found.</p>
        <Link href="/jobs" className="text-[12px] text-violet hover:underline">
          Back to jobs
        </Link>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 h-12 shrink-0 border-b border-border bg-background/80 backdrop-blur-sm">
        <button
          onClick={() => router.back()}
          className="flex items-center justify-center w-6 h-6 rounded-md hover:bg-surface-2 transition-colors text-text-tertiary hover:text-text-primary"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
        </button>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-[14px] font-semibold text-text-primary truncate">
            {job.job_title}
          </span>
          <span className="text-text-tertiary">/</span>
          <span className="text-[13px] text-text-secondary truncate">
            {job.company}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={job.applicationStatus} />
          {job.job_url && (
            <a
              href={job.job_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[12px] font-medium text-text-secondary hover:text-text-primary hover:bg-surface-2 transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              View job
            </a>
          )}
          {job.gmail_link && (
            <a
              href={job.gmail_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[12px] font-medium text-text-secondary hover:text-text-primary hover:bg-surface-2 transition-colors"
            >
              <Mail className="h-3 w-3" />
              Gmail
            </a>
          )}
        </div>
      </header>

      {/* Body: 2-column split */}
      <div className="flex-1 flex overflow-hidden">
        {/* Main content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          <JobContent job={job} />
        </div>

        {/* Right tracking panel */}
        <aside className="w-[300px] xl:w-[320px] shrink-0 border-l border-border overflow-auto">
          <TrackingPanel job={job} />
        </aside>
      </div>
    </div>
  );
}

/* ── Job content (left column) ─────────────────────────────────── */
function JobContent({ job }: { job: JobRecord }) {
  return (
    <div className="max-w-2xl space-y-6">
      {/* Title block */}
      <div>
        <div className="flex items-center gap-3 mb-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-surface-3 border border-divider text-[13px] font-bold text-text-secondary">
            {companyInitials(job.company)}
          </div>
          <div>
            <h1 className="text-[18px] font-semibold text-text-primary leading-tight">
              {job.job_title}
            </h1>
            <p className="text-[13px] text-text-secondary">
              {job.company}
              {job.location ? ` · ${job.location}` : ""}
            </p>
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-2 mt-2">
          {job.seniority && job.seniority !== "null" && (
            <span className="text-[11px] bg-surface-3 text-text-secondary px-2 py-0.5 rounded border border-divider">
              {job.seniority}
            </span>
          )}
          {job.employment_type && job.employment_type !== "null" && (
            <span className="text-[11px] bg-surface-3 text-text-secondary px-2 py-0.5 rounded border border-divider">
              {job.employment_type}
            </span>
          )}
          {job.remote_policy && (
            <span className="text-[11px] bg-surface-3 text-text-secondary px-2 py-0.5 rounded border border-divider">
              {job.remote_policy}
            </span>
          )}
          {job.compensation && (
            <span className="text-[11px] text-emerald-300 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/30">
              {job.compensation}
            </span>
          )}
          {job.confidence && (
            <span
              className={cn(
                "text-[11px] px-2 py-0.5 rounded border",
                job.confidence === "high"
                  ? "text-violet bg-violet-muted border-violet/20"
                  : job.confidence === "medium"
                    ? "text-amber-300 bg-amber-950/40 border-amber-800/30"
                    : "text-rose-300 bg-rose-950/40 border-rose-800/30",
              )}
            >
              {job.confidence} confidence
            </span>
          )}
        </div>
      </div>

      {/* Summary */}
      {job.summary && (
        <Section title="Summary">
          <p className="text-[13px] text-text-secondary leading-relaxed">
            {job.summary}
          </p>
        </Section>
      )}

      {/* Skills */}
      {(job.required_skills?.length ?? 0) > 0 ||
      (job.preferred_skills?.length ?? 0) > 0 ? (
        <Section title="Skills">
          {(job.required_skills?.length ?? 0) > 0 && (
            <div className="mb-3">
              <p className="text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
                Required
              </p>
              <div className="flex flex-wrap gap-1.5">
                {job.required_skills?.map((skill) => (
                  <SkillBadge key={skill} label={skill} variant="required" />
                ))}
              </div>
            </div>
          )}
          {(job.preferred_skills?.length ?? 0) > 0 && (
            <div>
              <p className="text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
                Preferred
              </p>
              <div className="flex flex-wrap gap-1.5">
                {job.preferred_skills?.map((skill) => (
                  <SkillBadge key={skill} label={skill} variant="preferred" />
                ))}
              </div>
            </div>
          )}
        </Section>
      ) : null}

      {/* Keywords */}
      {(job.keywords?.length ?? 0) > 0 && (
        <Section title="Keywords">
          <div className="flex flex-wrap gap-1.5">
            {job.keywords?.map((kw) => (
              <SkillBadge key={kw} label={kw} variant="keyword" />
            ))}
          </div>
        </Section>
      )}

      {/* Responsibilities */}
      {(job.responsibilities?.length ?? 0) > 0 && (
        <Section title="Responsibilities">
          <ul className="space-y-1.5">
            {job.responsibilities?.map((r, i) => (
              <li
                key={i}
                className="flex gap-2 text-[13px] text-text-secondary"
              >
                <span className="text-violet mt-0.5 shrink-0">·</span>
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Requirements */}
      {(job.requirements?.length ?? 0) > 0 && (
        <Section title="Requirements">
          <ul className="space-y-1.5">
            {job.requirements?.map((r, i) => (
              <li
                key={i}
                className="flex gap-2 text-[13px] text-text-secondary"
              >
                <CheckCircle className="h-3.5 w-3.5 text-violet mt-0.5 shrink-0" />
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Nice to have */}
      {(job.nice_to_have?.length ?? 0) > 0 && (
        <Section title="Nice to Have">
          <ul className="space-y-1.5">
            {job.nice_to_have?.map((r, i) => (
              <li
                key={i}
                className="flex gap-2 text-[13px] text-text-secondary"
              >
                <span className="text-blue-400 mt-0.5 shrink-0">+</span>
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Import metadata */}
      <Section title="Import Metadata">
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
          <MetaRow label="Imported" value={timeAgo(job.importedAt)} />
          <MetaRow label="Email date" value={formatDate(job.email_date)} />
          {job.subject && <MetaRow label="Subject" value={job.subject} />}
          {job.sender && <MetaRow label="Sender" value={job.sender} />}
          {job.visa_sponsorship && (
            <MetaRow label="Visa" value={job.visa_sponsorship} />
          )}
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="text-text-tertiary">{label}</span>
      <span className="text-text-secondary">{value}</span>
    </>
  );
}

/* ── Tracking panel (right column) ──────────────────────────────── */
function TrackingPanel({ job }: { job: JobRecord }) {
  const { register, handleSubmit } = useForm<TrackingForm>({
    resolver: zodResolver(trackingSchema),
    defaultValues: {
      applicationStatus: job.applicationStatus,
      dateApplied: job.dateApplied ?? "",
      nextFollowUpDate: job.nextFollowUpDate ?? "",
      referral: job.referral ?? "",
      contactName: job.contactName ?? "",
      contactEmail: job.contactEmail ?? "",
      salaryExpectation: job.salaryExpectation ?? "",
      notes: job.notes ?? "",
    },
  });

  async function onSubmit(data: TrackingForm) {
    if (!job.id) return;
    const now = new Date().toISOString();
    const updates: Partial<JobRecord> = {
      dateApplied: data.dateApplied || undefined,
      nextFollowUpDate: data.nextFollowUpDate || undefined,
      referral: data.referral || undefined,
      contactName: data.contactName || undefined,
      contactEmail: data.contactEmail || undefined,
      salaryExpectation: data.salaryExpectation || undefined,
      notes: data.notes || undefined,
      updatedAt: now,
    };

    const newStatus = data.applicationStatus as ApplicationStatus;

    if (newStatus !== job.applicationStatus) {
      const activity: ActivityItem = {
        id: uuidv4(),
        timestamp: now,
        text: "Status changed",
        fromStatus: job.applicationStatus,
        toStatus: newStatus,
        kind: "status_change",
      };
      updates.applicationStatus = newStatus;
      updates.activityLog = [...(job.activityLog ?? []), activity];
    }

    await db.jobs.update(job.id, updates);
  }

  async function addNote(text: string) {
    if (!job.id || !text.trim()) return;
    const now = new Date().toISOString();
    const activity: ActivityItem = {
      id: uuidv4(),
      timestamp: now,
      text: text.trim(),
      kind: "note",
    };
    await db.jobs.update(job.id, {
      activityLog: [...(job.activityLog ?? []), activity],
      updatedAt: now,
    });
  }

  async function toggleSaved() {
    if (!job.id) return;
    await db.jobs.update(job.id, {
      saved: !job.saved,
      updatedAt: new Date().toISOString(),
    });
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="p-4 space-y-4">
      {/* Status */}
      <div className="space-y-1.5">
        <label className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
          Status
        </label>
        <div className="relative">
          <select
            {...register("applicationStatus")}
            className={cn(
              "w-full appearance-none px-3 py-2 pr-8 rounded-md",
              "bg-surface-2 border border-divider",
              "text-[13px] text-text-primary",
              "focus:outline-none focus:ring-1 focus:ring-violet/50",
              "cursor-pointer",
            )}
          >
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_META[s].label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-tertiary pointer-events-none" />
        </div>
      </div>

      {/* Save button */}
      <button
        type="button"
        onClick={toggleSaved}
        className={cn(
          "flex items-center gap-2 w-full px-3 py-2 rounded-md",
          "text-[12px] font-medium transition-colors",
          job.saved
            ? "bg-blue-950/60 text-blue-300 border border-blue-800/30"
            : "bg-surface-2 text-text-secondary border border-divider hover:bg-surface-3",
        )}
      >
        {job.saved ? (
          <BookmarkCheck className="h-3.5 w-3.5" />
        ) : (
          <Bookmark className="h-3.5 w-3.5" />
        )}
        {job.saved ? "Saved" : "Save job"}
      </button>

      <hr className="border-divider" />

      {/* Date applied */}
      <FormField label="Date Applied">
        <input type="date" {...register("dateApplied")} className={inputCn} />
      </FormField>

      {/* Follow-up */}
      <FormField label="Next Follow-Up">
        <div className="relative">
          <input
            type="date"
            {...register("nextFollowUpDate")}
            className={cn(inputCn, "pr-8")}
          />
          <Calendar className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-tertiary pointer-events-none" />
        </div>
      </FormField>

      {/* Referral */}
      <FormField label="Referral">
        <input
          type="text"
          placeholder="Referral source"
          {...register("referral")}
          className={inputCn}
        />
      </FormField>

      {/* Contact */}
      <FormField label="Contact Name">
        <input
          type="text"
          placeholder="Recruiter / hiring manager"
          {...register("contactName")}
          className={inputCn}
        />
      </FormField>

      <FormField label="Contact Email">
        <input
          type="email"
          placeholder="email@company.com"
          {...register("contactEmail")}
          className={inputCn}
        />
      </FormField>

      {/* Salary */}
      <FormField label="Salary Expectation">
        <input
          type="text"
          placeholder="e.g. $120K–$140K"
          {...register("salaryExpectation")}
          className={inputCn}
        />
      </FormField>

      <hr className="border-divider" />

      {/* Notes */}
      <FormField label="Notes">
        <textarea
          placeholder="Add notes about this role…"
          {...register("notes")}
          rows={4}
          className={cn(inputCn, "resize-none leading-relaxed")}
        />
      </FormField>

      {/* Save tracking */}
      <button
        type="submit"
        className={cn(
          "w-full px-3 py-2 rounded-md",
          "text-[13px] font-medium",
          "bg-violet text-white",
          "hover:opacity-90 transition-opacity",
        )}
      >
        Save changes
      </button>

      <hr className="border-divider" />

      {/* Add note */}
      <QuickNote onAdd={addNote} />

      <hr className="border-divider" />

      {/* Activity log */}
      <div>
        <p className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-3">
          Activity
        </p>
        <ActivityFeed items={job.activityLog ?? []} compact />
      </div>
    </form>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium text-text-tertiary">
        {label}
      </label>
      {children}
    </div>
  );
}

const inputCn = cn(
  "w-full px-3 py-2 rounded-md",
  "bg-surface-2 border border-divider",
  "text-[13px] text-text-primary",
  "placeholder:text-text-tertiary",
  "focus:outline-none focus:ring-1 focus:ring-violet/50",
  "transition-colors",
);

function QuickNote({ onAdd }: { onAdd: (text: string) => void }) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      const target = e.currentTarget;
      if (target.value.trim()) {
        onAdd(target.value);
        target.value = "";
      }
    }
  };

  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-medium text-text-tertiary">
        Add Note
      </label>
      <textarea
        placeholder="Write a note… (⌘+Enter to save)"
        rows={2}
        onKeyDown={handleKeyDown}
        className={cn(inputCn, "resize-none")}
      />
    </div>
  );
}

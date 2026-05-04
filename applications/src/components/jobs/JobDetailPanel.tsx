"use client";

import Link from "next/link";
import { useLiveQuery } from "dexie-react-hooks";
import {
  ExternalLink,
  Mail,
  ArrowUpRight,
  DollarSign,
  MapPin,
  Globe,
  User,
  Briefcase,
  Calendar,
  Tag,
  Shield,
  AlertTriangle,
  CheckCircle,
  LayoutDashboard,
  GitGraphIcon,
} from "lucide-react";
import {
  cn,
  formatDate,
  companyInitials,
  getEnrichmentStatus,
} from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SkillBadge } from "@/components/ui/SkillBadge";
import { db } from "@/lib/db";
import type { JobRecord } from "@/types";

interface JobDetailPanelProps {
  jobId: number;
}

/**
 * Rich preview panel rendered in the split (gallery) view right pane.
 * Fetches the job live from Dexie so it reflects any status changes instantly.
 */
export function JobDetailPanel({ jobId }: JobDetailPanelProps) {
  const job = useLiveQuery(() => db.jobs.get(jobId), [jobId]);

  if (!job) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="h-5 w-5 rounded-full border-2 border-violet border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-5 space-y-5 overflow-auto">
      <JobDetailContent job={job} />
    </div>
  );
}

/** Inner detail content — kept separate so it only re-renders when `job` changes. */
function JobDetailContent({ job }: { job: JobRecord }) {
  const requiredSkills = job.required_skills ?? [];
  const preferredSkills = job.preferred_skills ?? [];
  const keywords = job.keywords ?? [];
  const responsibilities = job.responsibilities ?? [];
  const requirements = job.requirements ?? [];
  const niceToHave = job.nice_to_have ?? [];

  const enrichmentStatus = getEnrichmentStatus(job);
  const isWttj = job.source === "wttj_gmail";
  const isSimplify = job.source === "simplify_github";

  return (
    <div className="space-y-5">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex items-start gap-3">
        {/* Company avatar */}
        <div
          className={cn(
            "flex items-center justify-center w-11 h-11 rounded-xl shrink-0 mt-0.5",
            "bg-surface-3 border border-divider",
            "text-sm font-bold text-text-secondary",
          )}
        >
          {companyInitials(job.company)}
        </div>

        <div className="flex-1 min-w-0">
          <h2 className="text-[16px] font-bold text-text-primary leading-snug">
            {job.job_title}
          </h2>
          <p className="text-[13px] text-text-secondary mt-0.5">
            <span className="font-medium">{job.company}</span>
            {job.location ? ` · ${job.location}` : ""}
            {job.remote_policy && job.remote_policy !== "null"
              ? ` · ${job.remote_policy}`
              : ""}
          </p>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <StatusBadge status={job.applicationStatus} />
            {job.seniority && job.seniority !== "null" && (
              <span className="text-[11px] font-semibold text-text-tertiary bg-surface-3 px-2 py-1 rounded-md border border-divider">
                {job.seniority}
              </span>
            )}
            {/* Source badge */}
            {isWttj && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-violet bg-violet-muted px-2 py-1 rounded-md border border-violet/20">
                <Mail className="h-2.5 w-2.5" />
                Email
              </span>
            )}
            {isSimplify && (
              <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-text-tertiary bg-surface-3 px-2 py-1 rounded-md border border-divider">
                <GitGraphIcon className="h-2.5 w-2.5" />
                Simplify
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Enrichment status banner ────────────────────── */}
      {enrichmentStatus === "failed" && (
        <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-amber-50 border border-amber-200">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0 mt-0.5" />
          <p className="text-[12px] text-amber-800 leading-relaxed">
            Enrichment failed — the job page could not be parsed. Fields like
            skills, requirements, and summary may be empty.
          </p>
        </div>
      )}
      {enrichmentStatus === "none" && (
        <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-surface-3 border border-divider">
          <AlertTriangle className="h-3.5 w-3.5 text-text-tertiary shrink-0 mt-0.5" />
          <p className="text-[12px] text-text-tertiary leading-relaxed">
            Not yet enriched — run the enrichment pipeline to fill in skills,
            requirements, and a summary.
          </p>
        </div>
      )}
      {enrichmentStatus === "enriched" && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
          <p className="text-[12px] text-emerald-800 font-medium">Enriched</p>
        </div>
      )}

      {/* ── Action buttons ─────────────────────────────── */}
      <div className="flex items-center gap-2 flex-wrap">
        {job.job_url && (
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md",
              "bg-violet text-white text-xs font-semibold",
              "hover:opacity-90 transition-opacity",
            )}
          >
            <ExternalLink className="h-3.5 w-3.5" />
            View Job
          </a>
        )}
        {/* WTTJ: link to the WTTJ dashboard job page */}
        {isWttj && job.wttj_dashboard_url && (
          <a
            href={job.wttj_dashboard_url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md",
              "bg-surface-3 border border-divider text-text-secondary text-xs font-semibold",
              "hover:bg-surface-2 transition-colors",
            )}
          >
            <LayoutDashboard className="h-3.5 w-3.5" />
            WTTJ Page
          </a>
        )}
        {/* WTTJ: link to the original email */}
        {isWttj && job.gmail_link && (
          <a
            href={job.gmail_link}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md",
              "bg-surface-3 border border-divider text-text-secondary text-xs font-semibold",
              "hover:bg-surface-2 transition-colors",
            )}
          >
            <Mail className="h-3.5 w-3.5" />
            View Email
          </a>
        )}
        {/* Simplify: link to the Simplify GitHub source */}
        {isSimplify && job.simplify_url && (
          <a
            href={job.simplify_url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md",
              "bg-surface-3 border border-divider text-text-secondary text-xs font-semibold",
              "hover:bg-surface-2 transition-colors",
            )}
          >
            <GitGraphIcon className="h-3.5 w-3.5" />
            View on Simplify
          </a>
        )}
        <Link
          href={`/jobs/${job.id}`}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-md ml-auto",
            "bg-surface-3 border border-divider text-text-secondary text-xs font-semibold",
            "hover:bg-surface-2 transition-colors",
          )}
        >
          <ArrowUpRight className="h-3.5 w-3.5" />
          Full Detail
        </Link>
      </div>

      {/* ── Info grid ──────────────────────────────────── */}
      {(job.compensation ||
        job.employment_type ||
        job.visa_sponsorship ||
        job.email_date ||
        job.date_posted_human ||
        job.source) && (
        <div className="grid grid-cols-2 gap-2">
          {job.compensation && job.compensation !== "null" && (
            <InfoItem
              icon={DollarSign}
              label="Compensation"
              value={job.compensation}
              valueClassName="text-emerald-600"
            />
          )}
          {job.location && (
            <InfoItem icon={MapPin} label="Location" value={job.location} />
          )}
          {job.remote_policy && job.remote_policy !== "null" && (
            <InfoItem
              icon={Globe}
              label="Remote Policy"
              value={job.remote_policy}
            />
          )}
          {job.employment_type &&
            job.employment_type !== "null" &&
            job.employment_type !== "" && (
              <InfoItem
                icon={Briefcase}
                label="Employment"
                value={job.employment_type}
              />
            )}
          {job.seniority && job.seniority !== "null" && (
            <InfoItem icon={User} label="Seniority" value={job.seniority} />
          )}
          {job.visa_sponsorship && job.visa_sponsorship !== "null" && (
            <InfoItem
              icon={Shield}
              label="Visa Sponsorship"
              value={job.visa_sponsorship}
            />
          )}
          {/* WTTJ: show email date as "Matched" */}
          {isWttj && job.email_date && (
            <InfoItem
              icon={Calendar}
              label="Matched"
              value={formatDate(job.email_date)}
            />
          )}
          {/* Simplify: show date_posted_human as "Posted" */}
          {isSimplify && job.date_posted_human && (
            <InfoItem
              icon={Calendar}
              label="Posted"
              value={formatDate(job.date_posted_human)}
            />
          )}
          {/* Fallback for unknown sources */}
          {!isWttj &&
            !isSimplify &&
            (job.email_date ?? job.date_posted_human) && (
              <InfoItem
                icon={Calendar}
                label="Posted"
                value={formatDate(job.email_date ?? job.date_posted_human)}
              />
            )}
          {job.source && (
            <InfoItem icon={Tag} label="Source" value={job.source} />
          )}
          {/* WTTJ: show email subject */}
          {isWttj && (job.email_subject ?? job.subject) && (
            <InfoItem
              icon={Mail}
              label="Email Subject"
              value={(job.email_subject ?? job.subject) as string}
            />
          )}
        </div>
      )}

      <div className="border-t border-divider" />

      {/* ── Summary ────────────────────────────────────── */}
      {job.summary && (
        <Section title="Summary">
          <p className="text-[13px] text-text-secondary leading-relaxed">
            {job.summary}
          </p>
        </Section>
      )}

      {/* ── Skills ─────────────────────────────────────── */}
      {requiredSkills.length > 0 && (
        <Section title="Required Skills">
          <div className="flex flex-wrap gap-1.5">
            {requiredSkills.map((skill) => (
              <SkillBadge key={skill} label={skill} variant="required" />
            ))}
          </div>
        </Section>
      )}

      {preferredSkills.length > 0 && (
        <Section title="Preferred Skills">
          <div className="flex flex-wrap gap-1.5">
            {preferredSkills.map((skill) => (
              <SkillBadge key={skill} label={skill} variant="preferred" />
            ))}
          </div>
        </Section>
      )}

      {keywords.length > 0 && (
        <Section title="Keywords">
          <div className="flex flex-wrap gap-1.5">
            {keywords.map((kw) => (
              <SkillBadge key={kw} label={kw} variant="keyword" />
            ))}
          </div>
        </Section>
      )}

      {/* ── Responsibilities ───────────────────────────── */}
      {responsibilities.length > 0 && (
        <>
          <div className="border-t border-divider" />
          <Section title="Responsibilities">
            <BulletList items={responsibilities} />
          </Section>
        </>
      )}

      {/* ── Requirements ───────────────────────────────── */}
      {requirements.length > 0 && (
        <Section title="Requirements">
          <BulletList items={requirements} />
        </Section>
      )}

      {/* ── Nice to have ───────────────────────────────── */}
      {niceToHave.length > 0 && (
        <Section title="Nice to Have">
          <BulletList items={niceToHave} />
        </Section>
      )}
    </div>
  );
}

/* ── Helper sub-components ────────────────────────────────────────────── */

/** Labelled icon+value card used in the info grid. */
function InfoItem({
  icon: Icon,
  label,
  value,
  valueClassName,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-start gap-2 p-2.5 rounded-lg bg-surface-3 border border-divider min-w-0">
      <Icon className="h-3.5 w-3.5 text-text-tertiary shrink-0 mt-0.5" />
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-wider text-text-tertiary">
          {label}
        </p>
        <p
          className={cn(
            "text-[12px] font-semibold text-text-primary mt-0.5 truncate",
            valueClassName,
          )}
        >
          {value}
        </p>
      </div>
    </div>
  );
}

/** Section wrapper with a styled heading. */
function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2.5">
      <h3 className="text-[11px] font-bold uppercase tracking-wider text-text-tertiary">
        {title}
      </h3>
      {children}
    </div>
  );
}

/** Bulleted list of strings (responsibilities, requirements, etc.). */
function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li
          key={index}
          className="flex items-start gap-2.5 text-[13px] text-text-secondary leading-relaxed"
        >
          <span className="mt-[7px] h-1 w-1 rounded-full bg-text-tertiary/60 shrink-0" />
          {item}
        </li>
      ))}
    </ul>
  );
}

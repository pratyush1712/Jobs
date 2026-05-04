"use client";

import { memo, useCallback } from "react";
import { ExternalLink, Bookmark, BookmarkCheck, Mail } from "lucide-react";
import { cn, timeAgo, companyInitials } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CONFIDENCE_META } from "@/lib/constants";
import type { JobRecord } from "@/types";
import { getDb } from "@/lib/db";

interface JobCardProps {
  job: JobRecord;
  isSelected?: boolean;
  onClick?: () => void;
}

/**
 * Richer card component for the gallery (split) view left panel.
 * Shows company, title, location, compensation, seniority, employment type,
 * status badge, and date — all in a compact but scannable layout.
 *
 * Clicking this card calls onClick() to update the preview; it never navigates.
 */
export const JobCard = memo(function JobCard({
  job,
  isSelected = false,
  onClick,
}: JobCardProps) {
  const toggleSaved = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!job.id) return;
      const database = getDb();
      await database.jobs.update(job.id, {
        saved: !job.saved,
        updatedAt: new Date().toISOString(),
      });
    },
    [job.id, job.saved],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className={cn(
        "group px-4 py-3.5 border-b border-divider cursor-pointer",
        "transition-colors outline-none",
        isSelected
          ? "bg-violet-muted"
          : "hover:bg-surface-3/60 focus-visible:bg-surface-3/60",
      )}
    >
      <div className="flex items-start gap-3">
        {/* Company avatar */}
        <div
          className={cn(
            "flex items-center justify-center w-9 h-9 rounded-lg shrink-0 mt-0.5",
            "bg-surface-3 border border-divider",
            "text-xs font-bold text-text-secondary",
          )}
        >
          {companyInitials(job.company)}
        </div>

        <div className="flex-1 min-w-0 space-y-1.5">
          {/* Title row + status badge */}
          <div className="flex items-start gap-2">
            <p
              className={cn(
                "text-[13px] font-semibold leading-snug flex-1 min-w-0",
                isSelected ? "text-violet" : "text-text-primary",
              )}
            >
              {job.job_title}
            </p>
            <StatusBadge
              status={job.applicationStatus}
              className="shrink-0 mt-0.5"
            />
          </div>

          {/* Company · Location · Remote */}
          <p className="text-[12px] text-text-secondary truncate">
            <span className="font-medium">{job.company}</span>
            {job.location ? ` · ${job.location}` : ""}
            {job.remote_policy && job.remote_policy !== "null"
              ? ` · ${job.remote_policy}`
              : ""}
          </p>

          {/* Compensation — shown in green when present */}
          {job.compensation && job.compensation !== "null" && (
            <p className="text-[12px] font-medium text-emerald-600 truncate">
              {job.compensation}
            </p>
          )}

          {/* Bottom row: seniority + type badges, confidence, hover actions, timestamp */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {job.seniority && job.seniority !== "null" && (
              <span className="text-[11px] text-text-tertiary bg-surface-3 px-1.5 py-0.5 rounded border border-divider leading-none">
                {job.seniority}
              </span>
            )}
            {job.employment_type &&
              job.employment_type !== "null" &&
              job.employment_type !== "" && (
                <span className="text-[11px] text-text-tertiary bg-surface-3 px-1.5 py-0.5 rounded border border-divider leading-none">
                  {job.employment_type}
                </span>
              )}

            {/* Confidence badge */}
            {job.confidence &&
              job.confidence in CONFIDENCE_META &&
              (() => {
                const meta =
                  CONFIDENCE_META[
                    job.confidence as keyof typeof CONFIDENCE_META
                  ];
                return (
                  <span
                    className={cn(
                      "flex items-center gap-1 text-[11px] font-semibold px-1.5 py-0.5 rounded leading-none",
                      meta.bgColor,
                      meta.color,
                    )}
                    title={`Enrichment confidence: ${meta.label}`}
                  >
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full shrink-0",
                        meta.dotColor,
                      )}
                    />
                    {meta.label}
                  </span>
                );
              })()}

            {/* Hover-only action icons */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {job.job_url && (
                <a
                  href={job.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center justify-center w-5 h-5 rounded text-text-tertiary hover:text-text-primary transition-colors"
                  title="Open job posting"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {job.gmail_link && (
                <a
                  href={job.gmail_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center justify-center w-5 h-5 rounded text-text-tertiary hover:text-text-primary transition-colors"
                  title="Open Gmail"
                >
                  <Mail className="h-3 w-3" />
                </a>
              )}
              <button
                onClick={toggleSaved}
                className="flex items-center justify-center w-5 h-5 rounded text-text-tertiary hover:text-text-primary transition-colors"
                title={job.saved ? "Unsave" : "Save"}
              >
                {job.saved ? (
                  <BookmarkCheck className="h-3 w-3 text-violet" />
                ) : (
                  <Bookmark className="h-3 w-3" />
                )}
              </button>
            </div>

            {/* Timestamp pushed to the right */}
            <span className="ml-auto text-[11px] text-text-tertiary tabular-nums">
              {timeAgo(job.email_date ?? job.importedAt)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

"use client";

import { memo, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  ExternalLink,
  Mail,
  Bookmark,
  BookmarkCheck,
  ArrowUpRight,
} from "lucide-react";
import { cn, timeAgo, companyInitials } from "@/lib/utils";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CONFIDENCE_META } from "@/lib/constants";
import type { JobRecord } from "@/types";
import { getDb } from "@/lib/db";

interface JobRowProps {
  job: JobRecord;
  isSelected?: boolean;
  isActive?: boolean;
  /**
   * Called whenever the row is clicked (before any navigation).
   * Used in split view to update the selected job.
   */
  onClick?: () => void;
  /**
   * When true, clicking the row will NOT navigate to `/jobs/:id`.
   * Useful in split view where the row click should only select the job.
   */
  disableNavigation?: boolean;
}

/**
 * Wrapped with React.memo so rows that haven't changed skip re-rendering
 * when a sibling row or parent filter state triggers a reconciliation pass.
 *
 * Uses a <div> instead of <Link> to avoid illegal nested <a> tags — the
 * row contains child <a> elements for external job URL / Gmail links.
 * Navigation is handled programmatically via router.push.
 */
export const JobRow = memo(function JobRow({
  job,
  isSelected = false,
  isActive = false,
  onClick,
  disableNavigation = false,
}: JobRowProps) {
  const router = useRouter();

  /**
   * Shared activation handler for both mouse click and keyboard events.
   * Calls onClick (e.g. selectJob) first, then navigates unless disabled.
   */
  const handleActivate = useCallback(() => {
    onClick?.();
    if (!disableNavigation) {
      router.push(`/jobs/${job.id}`);
    }
  }, [job.id, onClick, router, disableNavigation]);

  const handleRowClick = useCallback(
    (e: React.MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("a") || target.closest("button")) return;
      handleActivate();
    },
    [handleActivate],
  );

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
      role="link"
      tabIndex={0}
      onClick={handleRowClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleActivate();
        }
      }}
      className={cn(
        "group flex items-center gap-4 px-5 py-3.5 border-b border-divider",
        "transition-colors cursor-pointer",
        isActive
          ? "bg-violet-muted"
          : isSelected
            ? "bg-surface-3"
            : "hover:bg-surface-3/60",
      )}
    >
      {/* Company avatar */}
      <div
        className={cn(
          "flex items-center justify-center w-9 h-9 rounded-lg shrink-0",
          "bg-surface-3 border border-divider",
          "text-xs font-bold text-text-secondary",
        )}
      >
        {companyInitials(job.company)}
      </div>

      {/* Title + company */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text-primary leading-tight truncate">
          {job.job_title}
        </p>
        <p className="text-sm text-text-secondary truncate mt-0.5">
          {job.company}
          {job.location ? ` · ${job.location}` : ""}
          {job.compensation ? ` · ${job.compensation}` : ""}
        </p>
      </div>

      {/* Seniority */}
      {job.seniority && job.seniority !== "null" && (
        <span className="hidden lg:block text-xs text-text-tertiary shrink-0 bg-surface-3 px-2 py-1 rounded-md border border-divider">
          {job.seniority}
        </span>
      )}

      {/* Confidence badge — only shown when confidence is present */}
      {job.confidence &&
        job.confidence in CONFIDENCE_META &&
        (() => {
          const meta =
            CONFIDENCE_META[job.confidence as keyof typeof CONFIDENCE_META];
          return (
            <span
              className={cn(
                "hidden md:flex items-center gap-1 shrink-0",
                "text-xs font-semibold px-2 py-1 rounded-md",
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

      {/* Status */}
      <StatusBadge status={job.applicationStatus} className="shrink-0" />

      {/* Actions (shown on hover) */}
      <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        {job.job_url && (
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-3 transition-colors"
            title="Open job posting"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        {job.gmail_link && (
          <a
            href={job.gmail_link}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-3 transition-colors"
            title="Open Gmail"
          >
            <Mail className="h-3.5 w-3.5" />
          </a>
        )}
        <button
          onClick={toggleSaved}
          className="flex items-center justify-center w-7 h-7 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-3 transition-colors"
          title={job.saved ? "Unsave" : "Save"}
        >
          {job.saved ? (
            <BookmarkCheck className="h-3.5 w-3.5 text-violet" />
          ) : (
            <Bookmark className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* Time */}
      <span className="hidden xl:block text-xs text-text-tertiary tabular-nums shrink-0 w-24 text-right">
        {timeAgo(job.email_date ?? job.importedAt)}
      </span>

      {/* Navigate arrow — only shown when navigation is enabled */}
      {!disableNavigation && (
        <ArrowUpRight className="h-3.5 w-3.5 text-text-tertiary opacity-0 group-hover:opacity-50 transition-opacity shrink-0" />
      )}
    </div>
  );
});

"use client";

import { useMemo, useCallback, useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { useUIStore, applyFiltersAndSort } from "@/lib/store";
import { db } from "@/lib/db";
import { PageHeader } from "@/components/shell/PageHeader";
import { FilterBar } from "@/components/jobs/FilterBar";
import { JobRow } from "@/components/jobs/JobRow";
import { JobCard } from "@/components/jobs/JobCard";
import { JobDetailPanel } from "@/components/jobs/JobDetailPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { cn } from "@/lib/utils";
import Link from "next/link";
import {
  Upload,
  ArrowUpDown,
  ArrowDown,
  ArrowUp,
  Briefcase,
} from "lucide-react";
import { SORT_OPTIONS } from "@/lib/constants";
import type { SortField } from "@/types";

/** Minimum and maximum widths (px) for the left job-list pane in split view. */
const LIST_MIN_WIDTH = 240;
const LIST_MAX_WIDTH = 600;

export default function JobsPage() {
  const { filters, sort, viewMode, setSort, selectJob, selectedJobId } =
    useUIStore();

  /** Width of the left list pane in split view — draggable by the divider. */
  const [listWidth, setListWidth] = useState(340);

  const allJobs = useLiveQuery(
    () => db.jobs.orderBy("importedAt").reverse().toArray(),
    [],
  );

  /**
   * Memoize the filter + sort pass so it only recalculates when the raw
   * data or the filter/sort state actually change — not on unrelated renders.
   */
  const filteredJobs = useMemo(() => {
    if (!allJobs) return [];
    return applyFiltersAndSort(allJobs, filters, sort);
  }, [allJobs, filters, sort]);

  const toggleSort = useCallback(
    (field: SortField) => {
      if (sort.field === field) {
        setSort({
          field,
          direction: sort.direction === "asc" ? "desc" : "asc",
        });
      } else {
        setSort({ field, direction: "desc" });
      }
    },
    [sort.field, sort.direction, setSort],
  );

  /**
   * Starts a drag-to-resize session on the split-pane divider.
   * Inline closure pattern: captures startX and startWidth at mousedown,
   * then adds temporary global listeners for mousemove/mouseup.
   */
  const onDividerMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      const startX = e.clientX;
      const startWidth = listWidth;

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      function onMouseMove(ev: MouseEvent) {
        const delta = ev.clientX - startX;
        const clamped = Math.max(
          LIST_MIN_WIDTH,
          Math.min(LIST_MAX_WIDTH, startWidth + delta),
        );
        setListWidth(clamped);
      }

      function onMouseUp() {
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
      }

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [listWidth],
  );

  if (allJobs === undefined) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="h-5 w-5 rounded-full border-2 border-violet border-t-transparent animate-spin" />
      </div>
    );
  }

  function SortIcon({ field }: { field: SortField }) {
    if (sort.field !== field)
      return <ArrowUpDown className="h-3 w-3 text-text-tertiary" />;
    return sort.direction === "asc" ? (
      <ArrowUp className="h-3 w-3 text-violet" />
    ) : (
      <ArrowDown className="h-3 w-3 text-violet" />
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <PageHeader title="Jobs" description={`${filteredJobs.length} jobs`}>
        <Link
          href="/import"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <Upload className="h-4 w-4" />
          Import
        </Link>
      </PageHeader>

      <FilterBar
        totalCount={allJobs.length}
        filteredCount={filteredJobs.length}
      />

      {/* Sort bar */}
      <div className="flex items-center gap-1.5 px-5 py-2.5 border-b border-divider bg-background shrink-0">
        <span className="text-xs font-semibold text-text-tertiary mr-1 uppercase tracking-wider">
          Sort:
        </span>
        {SORT_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => toggleSort(opt.value as SortField)}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md",
              "text-xs font-semibold transition-colors",
              sort.field === opt.value
                ? "bg-violet-muted text-violet border border-violet/20"
                : "text-text-tertiary hover:text-text-secondary hover:bg-surface-3",
            )}
          >
            {opt.label}
            <SortIcon field={opt.value as SortField} />
          </button>
        ))}
      </div>

      {/* ── Content ─────────────────────────────────────── */}
      {allJobs.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <EmptyState />
        </div>
      ) : filteredJobs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 py-16">
          <p className="text-base text-text-secondary font-medium">
            No jobs match your filters.
          </p>
          <button
            onClick={() => useUIStore.getState().resetFilters()}
            className="text-sm text-violet font-semibold hover:underline"
          >
            Clear filters
          </button>
        </div>
      ) : viewMode === "table" ? (
        /* ── Table view ─────────────────────────────────── */
        <div className="flex-1 overflow-auto">
          {filteredJobs.map((job) => (
            <JobRow
              key={job.id}
              job={job}
              isActive={selectedJobId === job.id}
              onClick={() => selectJob(job.id ?? null)}
            />
          ))}
        </div>
      ) : (
        /* ── Split / gallery view ───────────────────────── */
        <div className="flex-1 flex overflow-hidden">
          {/* Left: job card list */}
          <div
            className="shrink-0 overflow-auto border-r border-border"
            style={{ width: listWidth }}
          >
            {filteredJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJobId === job.id}
                onClick={() => selectJob(job.id ?? null)}
              />
            ))}
          </div>

          {/* Drag divider — 8px hit area with a 1px visible border */}
          <div
            onMouseDown={onDividerMouseDown}
            className={cn(
              "w-2 shrink-0 cursor-col-resize group relative",
              "hover:bg-violet/10 active:bg-violet/15 transition-colors",
            )}
            title="Drag to resize"
          >
            <div className="absolute inset-y-0 left-[3px] w-px bg-border group-hover:bg-violet/40 transition-colors" />
          </div>

          {/* Right: detail preview panel */}
          <div className="flex-1 overflow-auto">
            {selectedJobId ? (
              <JobDetailPanel jobId={selectedJobId} />
            ) : (
              <EmptyPreview />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Empty state shown in the right pane before a job is selected. */
function EmptyPreview() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-8">
      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-surface-3 border border-divider mb-1">
        <Briefcase className="h-5 w-5 text-text-tertiary" />
      </div>
      <p className="text-[14px] font-medium text-text-secondary">
        Select a job to preview
      </p>
      <p className="text-[12px] text-text-tertiary max-w-[200px] leading-relaxed">
        Click any job from the list to see its full details here.
      </p>
    </div>
  );
}

"use client";

import { useMemo, useCallback } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { useUIStore, applyFiltersAndSort } from "@/lib/store";
import { db } from "@/lib/db";
import { PageHeader } from "@/components/shell/PageHeader";
import { FilterBar } from "@/components/jobs/FilterBar";
import { JobRow } from "@/components/jobs/JobRow";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { Upload, ArrowUpDown, ArrowDown, ArrowUp } from "lucide-react";
import { SORT_OPTIONS } from "@/lib/constants";
import type { SortField } from "@/types";

export default function JobsPage() {
  const { filters, sort, viewMode, setSort, selectJob, selectedJobId } =
    useUIStore();

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

      {/* Content */}
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
        /* Table view */
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
        /* Split pane view */
        <div className="flex-1 flex overflow-hidden">
          {/* Left list */}
          <div className="w-[340px] shrink-0 border-r border-border overflow-auto">
            {filteredJobs.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                isActive={selectedJobId === job.id}
                onClick={() => selectJob(job.id ?? null)}
              />
            ))}
          </div>

          {/* Right detail panel */}
          <div className="flex-1 overflow-auto">
            {selectedJobId ? (
              <JobDetailInline jobId={selectedJobId} />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-[13px] text-text-tertiary">
                  Select a job to view details
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Inline detail panel for split view */
function JobDetailInline({ jobId }: { jobId: number }) {
  return (
    <div className="p-6">
      <Link
        href={`/jobs/${jobId}`}
        className="inline-flex items-center gap-1.5 text-[12px] text-violet hover:underline mb-4"
      >
        Open full detail
      </Link>
      <JobDetailContent jobId={jobId} />
    </div>
  );
}

function JobDetailContent({ jobId }: { jobId: number }) {
  const job = useLiveQuery(() => db.jobs.get(jobId), [jobId]);
  if (!job) return null;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[16px] font-semibold text-text-primary">
          {job.job_title}
        </h2>
        <p className="text-[13px] text-text-secondary mt-0.5">
          {job.company}
          {job.location ? ` · ${job.location}` : ""}
        </p>
      </div>
      {job.summary && (
        <p className="text-[13px] text-text-secondary leading-relaxed">
          {job.summary}
        </p>
      )}
    </div>
  );
}

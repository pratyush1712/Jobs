"use client";

import { useRef } from "react";
import {
  Search,
  X,
  SlidersHorizontal,
  Grid2X2,
  List,
  Mail,
  GitBranch,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore, hasActiveFilters, activeFilterCount } from "@/lib/store";
import {
  ALL_STATUSES,
  STATUS_META,
  CONFIDENCE_LEVELS,
  CONFIDENCE_META,
} from "@/lib/constants";
import type { ApplicationStatus, ViewMode } from "@/types";

const SOURCE_OPTIONS = [
  { value: "wttj_gmail", label: "Email", Icon: Mail },
  { value: "simplify_github", label: "Simplify", Icon: GitBranch },
] as const;

interface FilterBarProps {
  totalCount: number;
  filteredCount: number;
}

export function FilterBar({ totalCount, filteredCount }: FilterBarProps) {
  const { filters, setFilter, resetFilters, viewMode, setViewMode } =
    useUIStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const isFiltered = hasActiveFilters(filters);
  const activeCount = activeFilterCount(filters);

  function toggleStatus(s: ApplicationStatus) {
    const current = filters.statuses;
    if (current.includes(s)) {
      setFilter(
        "statuses",
        current.filter((x) => x !== s),
      );
    } else {
      setFilter("statuses", [...current, s]);
    }
  }

  function toggleSource(s: string) {
    const current = filters.source;
    if (current.includes(s)) {
      setFilter(
        "source",
        current.filter((x) => x !== s),
      );
    } else {
      setFilter("source", [...current, s]);
    }
  }

  function toggleConfidence(level: string) {
    const current = filters.confidence;
    if (current.includes(level)) {
      setFilter(
        "confidence",
        current.filter((x) => x !== level),
      );
    } else {
      setFilter("confidence", [...current, level]);
    }
  }

  return (
    <div className="shrink-0 border-b border-border bg-background/90 backdrop-blur-sm">
      {/* Search row */}
      <div className="flex items-center gap-3 px-5 py-3">
        <div className="flex-1 flex items-center gap-2.5 bg-surface-3 border border-divider rounded-lg px-3.5 h-10">
          <Search className="h-4 w-4 text-text-tertiary shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search jobs, companies, skills…"
            value={filters.query}
            onChange={(e) => setFilter("query", e.target.value)}
            className={cn(
              "flex-1 bg-transparent text-sm text-text-primary",
              "placeholder:text-text-tertiary",
              "outline-none border-none",
              "caret-violet",
            )}
          />
          {filters.query && (
            <button
              onClick={() => setFilter("query", "")}
              className="text-text-tertiary hover:text-text-secondary transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Filter count badge */}
        {isFiltered && (
          <button
            onClick={resetFilters}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 rounded-lg",
              "text-xs font-semibold",
              "bg-violet-muted text-violet border border-violet/20",
              "hover:bg-violet/15 transition-colors",
            )}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            {activeCount} filter{activeCount !== 1 ? "s" : ""}
            <X className="h-3 w-3" />
          </button>
        )}

        {/* Result count */}
        <span className="text-sm text-text-tertiary tabular-nums shrink-0 font-medium">
          {filteredCount === totalCount
            ? `${totalCount} jobs`
            : `${filteredCount} / ${totalCount}`}
        </span>

        {/* View mode toggle */}
        <div className="flex items-center gap-0.5 bg-surface-3 border border-divider rounded-lg p-1">
          {(["table", "split"] as ViewMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={cn(
                "flex items-center justify-center w-7 h-7 rounded-md",
                "transition-colors",
                viewMode === mode
                  ? "bg-white text-text-primary shadow-sm"
                  : "text-text-tertiary hover:text-text-secondary",
              )}
            >
              {mode === "table" ? (
                <List className="h-4 w-4" />
              ) : (
                <Grid2X2 className="h-4 w-4" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Status chips */}
      <div className="flex items-center gap-2 px-5 pb-3 overflow-x-auto">
        <span className="text-xs font-semibold text-text-tertiary shrink-0 mr-1 uppercase tracking-wider">
          Status
        </span>
        {ALL_STATUSES.filter((s) => s !== "archived").map((status) => {
          const meta = STATUS_META[status];
          const active = filters.statuses.includes(status);
          return (
            <button
              key={status}
              onClick={() => toggleStatus(status)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
                "text-xs font-semibold transition-colors",
                active
                  ? cn(
                      meta.bgColor,
                      meta.color,
                      "ring-1 ring-inset ring-current/30",
                    )
                  : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
              )}
            >
              {active && (
                <span
                  className={cn("h-1.5 w-1.5 rounded-full", meta.dotColor)}
                />
              )}
              {meta.label}
            </button>
          );
        })}

        <span className="mx-1 text-text-tertiary">|</span>

        <button
          onClick={() =>
            setFilter("saved", filters.saved === true ? null : true)
          }
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
            "text-xs font-semibold transition-colors",
            filters.saved === true
              ? "bg-blue-100 text-blue-700 ring-1 ring-inset ring-blue-300"
              : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
          )}
        >
          Saved
        </button>

        <button
          onClick={() =>
            setFilter("archived", filters.archived === false ? null : false)
          }
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
            "text-xs font-semibold transition-colors",
            filters.archived === false
              ? "bg-surface-2 text-text-primary ring-1 ring-inset ring-border"
              : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
          )}
        >
          Active only
        </button>
      </div>

      {/* Source + Enrichment chips */}
      <div className="flex items-center gap-2 px-5 pb-3 overflow-x-auto">
        <span className="text-xs font-semibold text-text-tertiary shrink-0 mr-1 uppercase tracking-wider">
          Source
        </span>
        {SOURCE_OPTIONS.map(({ value, label, Icon }) => {
          const active = filters.source.includes(value);
          return (
            <button
              key={value}
              onClick={() => toggleSource(value)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
                "text-xs font-semibold transition-colors",
                active
                  ? "bg-violet-muted text-violet ring-1 ring-inset ring-violet/30"
                  : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
              )}
            >
              <Icon className="h-3 w-3" />
              {label}
            </button>
          );
        })}

        <span className="mx-1 text-text-tertiary">|</span>

        <span className="text-xs font-semibold text-text-tertiary shrink-0 mr-1 uppercase tracking-wider">
          Enrichment
        </span>

        {/* Enriched chip */}
        <button
          onClick={() =>
            setFilter("enriched", filters.enriched === true ? null : true)
          }
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
            "text-xs font-semibold transition-colors",
            filters.enriched === true
              ? "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-300"
              : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
          )}
        >
          <CheckCircle className="h-3 w-3" />
          Enriched
        </button>

        {/* Not Enriched / Failed chip */}
        <button
          onClick={() =>
            setFilter("enriched", filters.enriched === false ? null : false)
          }
          className={cn(
            "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
            "text-xs font-semibold transition-colors",
            filters.enriched === false
              ? "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-300"
              : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
          )}
        >
          <AlertCircle className="h-3 w-3" />
          Not Enriched
        </button>

        <span className="mx-1 text-text-tertiary">|</span>

        <span className="text-xs font-semibold text-text-tertiary shrink-0 mr-1 uppercase tracking-wider">
          Confidence
        </span>

        {/* High / Medium / Low confidence chips */}
        {CONFIDENCE_LEVELS.map((level) => {
          const meta = CONFIDENCE_META[level];
          const active = filters.confidence.includes(level);
          return (
            <button
              key={level}
              onClick={() => toggleConfidence(level)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md shrink-0",
                "text-xs font-semibold transition-colors",
                active
                  ? cn(
                      meta.bgColor,
                      meta.color,
                      "ring-1 ring-inset ring-current/30",
                    )
                  : "bg-surface-3 text-text-tertiary hover:bg-surface-2 border border-divider",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  active ? meta.dotColor : "bg-text-tertiary",
                )}
              />
              {meta.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

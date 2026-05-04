/**
 * Zustand store for UI state.
 * Keeps ephemeral UI concerns separate from persisted Dexie data.
 */

import { create } from "zustand";
import type {
  ApplicationStatus,
  JobFilters,
  SortState,
  ViewMode,
} from "@/types";

interface UIState {
  /* Jobs page */
  filters: JobFilters;
  sort: SortState;
  viewMode: ViewMode;
  selectedJobId: number | null;
  selectedIds: Set<number>;

  /* Command bar */
  commandOpen: boolean;

  /* Import drawer */
  importOpen: boolean;

  /* Actions */
  setFilter: <K extends keyof JobFilters>(key: K, val: JobFilters[K]) => void;
  resetFilters: () => void;
  setSort: (sort: SortState) => void;
  setViewMode: (mode: ViewMode) => void;
  selectJob: (id: number | null) => void;
  toggleSelect: (id: number) => void;
  clearSelection: () => void;
  selectAll: (ids: number[]) => void;
  setCommandOpen: (open: boolean) => void;
  setImportOpen: (open: boolean) => void;
}

const DEFAULT_FILTERS: JobFilters = {
  query: "",
  statuses: [],
  remotePolicy: [],
  employmentType: [],
  seniority: [],
  confidence: [],
  saved: null,
  archived: null,
};

export const useUIStore = create<UIState>((set) => ({
  filters: DEFAULT_FILTERS,
  sort: { field: "importedAt", direction: "desc" },
  viewMode: "table",
  selectedJobId: null,
  selectedIds: new Set(),
  commandOpen: false,
  importOpen: false,

  setFilter: (key, val) =>
    set((state) => ({
      filters: { ...state.filters, [key]: val },
    })),

  resetFilters: () => set({ filters: DEFAULT_FILTERS }),

  setSort: (sort) => set({ sort }),

  setViewMode: (mode) => set({ viewMode: mode }),

  selectJob: (id) => set({ selectedJobId: id }),

  toggleSelect: (id) =>
    set((state) => {
      const next = new Set(state.selectedIds);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return { selectedIds: next };
    }),

  clearSelection: () => set({ selectedIds: new Set() }),

  selectAll: (ids) => set({ selectedIds: new Set(ids) }),

  setCommandOpen: (open) => set({ commandOpen: open }),

  setImportOpen: (open) => set({ importOpen: open }),
}));

/** Selector: returns true if any filters are active. */
export function hasActiveFilters(filters: JobFilters): boolean {
  return (
    filters.query.trim().length > 0 ||
    filters.statuses.length > 0 ||
    filters.remotePolicy.length > 0 ||
    filters.employmentType.length > 0 ||
    filters.seniority.length > 0 ||
    filters.confidence.length > 0 ||
    filters.saved !== null ||
    filters.archived !== null
  );
}

/** Selector: counts active filter dimensions. */
export function activeFilterCount(filters: JobFilters): number {
  let count = 0;
  if (filters.query.trim().length > 0) count++;
  if (filters.statuses.length > 0) count++;
  if (filters.remotePolicy.length > 0) count++;
  if (filters.employmentType.length > 0) count++;
  if (filters.seniority.length > 0) count++;
  if (filters.confidence.length > 0) count++;
  if (filters.saved !== null) count++;
  if (filters.archived !== null) count++;
  return count;
}

/** Applies in-memory filters and sort to a list of jobs. */
export function applyFiltersAndSort<
  T extends {
    company?: string;
    job_title?: string;
    location?: string;
    keywords?: string[];
    required_skills?: string[];
    preferred_skills?: string[];
    applicationStatus: ApplicationStatus;
    remote_policy?: string;
    employment_type?: string;
    seniority?: string;
    confidence?: string;
    saved: boolean;
    archived: boolean;
    importedAt: string;
    email_date?: string;
    dateApplied?: string;
  },
>(items: T[], filters: JobFilters, sort: SortState): T[] {
  let result = [...items];

  // Text search
  if (filters.query.trim()) {
    const q = filters.query.toLowerCase();
    result = result.filter((job) => {
      const searchable = [
        job.company ?? "",
        job.job_title ?? "",
        job.location ?? "",
        ...(job.keywords ?? []),
        ...(job.required_skills ?? []),
        ...(job.preferred_skills ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return searchable.includes(q);
    });
  }

  // Status filter
  if (filters.statuses.length > 0) {
    result = result.filter((job) =>
      filters.statuses.includes(job.applicationStatus),
    );
  }

  // Remote policy filter
  if (filters.remotePolicy.length > 0) {
    result = result.filter((job) => {
      const rp = (job.remote_policy ?? "").toLowerCase();
      return filters.remotePolicy.some((f) => rp.includes(f.toLowerCase()));
    });
  }

  // Employment type filter
  if (filters.employmentType.length > 0) {
    result = result.filter((job) =>
      filters.employmentType.some((f) =>
        (job.employment_type ?? "").toLowerCase().includes(f.toLowerCase()),
      ),
    );
  }

  // Seniority filter
  if (filters.seniority.length > 0) {
    result = result.filter((job) =>
      filters.seniority.some((f) =>
        (job.seniority ?? "").toLowerCase().includes(f.toLowerCase()),
      ),
    );
  }

  // Confidence filter
  if (filters.confidence.length > 0) {
    result = result.filter((job) =>
      filters.confidence.includes(job.confidence ?? ""),
    );
  }

  // Saved filter
  if (filters.saved !== null) {
    result = result.filter((job) => job.saved === filters.saved);
  }

  // Archived filter
  if (filters.archived !== null) {
    result = result.filter((job) => job.archived === filters.archived);
  }

  // Sort
  result.sort((a, b) => {
    let aVal = "";
    let bVal = "";

    switch (sort.field) {
      case "importedAt":
        aVal = a.importedAt ?? "";
        bVal = b.importedAt ?? "";
        break;
      case "email_date":
        aVal = a.email_date ?? "";
        bVal = b.email_date ?? "";
        break;
      case "dateApplied":
        aVal = a.dateApplied ?? "";
        bVal = b.dateApplied ?? "";
        break;
      case "company":
        aVal = (a.company ?? "").toLowerCase();
        bVal = (b.company ?? "").toLowerCase();
        break;
      case "job_title":
        aVal = (a.job_title ?? "").toLowerCase();
        bVal = (b.job_title ?? "").toLowerCase();
        break;
    }

    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sort.direction === "asc" ? cmp : -cmp;
  });

  return result;
}

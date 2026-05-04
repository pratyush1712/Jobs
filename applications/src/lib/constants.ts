/**
 * Shared constants: status labels, colors, and filter options.
 */

import type { ApplicationStatus } from "@/types";

export interface StatusMeta {
  label: string;
  color: string;
  bgColor: string;
  dotColor: string;
  order: number;
}

export const STATUS_META: Record<ApplicationStatus, StatusMeta> = {
  interested: {
    label: "Interested",
    color: "text-slate-600",
    bgColor: "bg-slate-100",
    dotColor: "bg-slate-400",
    order: 0,
  },
  saved: {
    label: "Saved",
    color: "text-blue-700",
    bgColor: "bg-blue-100",
    dotColor: "bg-blue-500",
    order: 1,
  },
  applied: {
    label: "Applied",
    color: "text-violet-700",
    bgColor: "bg-violet-100",
    dotColor: "bg-violet-500",
    order: 2,
  },
  oa: {
    label: "OA",
    color: "text-indigo-700",
    bgColor: "bg-indigo-100",
    dotColor: "bg-indigo-500",
    order: 3,
  },
  recruiter_screen: {
    label: "Recruiter Screen",
    color: "text-cyan-700",
    bgColor: "bg-cyan-100",
    dotColor: "bg-cyan-500",
    order: 4,
  },
  interview: {
    label: "Interview",
    color: "text-sky-700",
    bgColor: "bg-sky-100",
    dotColor: "bg-sky-500",
    order: 5,
  },
  final_round: {
    label: "Final Round",
    color: "text-amber-700",
    bgColor: "bg-amber-100",
    dotColor: "bg-amber-500",
    order: 6,
  },
  offer: {
    label: "Offer",
    color: "text-emerald-700",
    bgColor: "bg-emerald-100",
    dotColor: "bg-emerald-500",
    order: 7,
  },
  rejected: {
    label: "Rejected",
    color: "text-rose-700",
    bgColor: "bg-rose-100",
    dotColor: "bg-rose-500",
    order: 8,
  },
  archived: {
    label: "Archived",
    color: "text-zinc-500",
    bgColor: "bg-zinc-100",
    dotColor: "bg-zinc-400",
    order: 9,
  },
};

export const ALL_STATUSES = Object.keys(STATUS_META) as ApplicationStatus[];

export const ACTIVE_STATUSES: ApplicationStatus[] = [
  "interested",
  "saved",
  "applied",
  "oa",
  "recruiter_screen",
  "interview",
  "final_round",
];

export const PIPELINE_STATUSES: ApplicationStatus[] = [
  "interested",
  "saved",
  "applied",
  "oa",
  "recruiter_screen",
  "interview",
  "final_round",
  "offer",
  "rejected",
];

/** Chart color palette — matches CSS vars but as hex for Recharts */
export const CHART_COLORS = [
  "oklch(0.66 0.2 270)", // violet  — primary
  "oklch(0.62 0.17 220)", // blue
  "oklch(0.7 0.14 180)", // teal
  "oklch(0.72 0.14 140)", // green
  "oklch(0.68 0.16 50)", // amber
  "oklch(0.65 0.2 10)", // rose
];

export const CHART_COLORS_HEX = [
  "#7c6df7",
  "#5b90f0",
  "#4db8b8",
  "#5cba6a",
  "#d4954a",
  "#d46060",
];

export const REMOTE_POLICIES = [
  "Remote",
  "Hybrid",
  "Onsite",
  "Flexible",
] as const;

export const EMPLOYMENT_TYPES = [
  "Full-Time",
  "Part-Time",
  "Contract",
  "Internship",
] as const;

export const SENIORITY_LEVELS = [
  "New Grad",
  "Entry Level",
  "Junior",
  "Mid",
  "Senior",
  "Staff",
  "Principal",
  "Internship",
] as const;

export const CONFIDENCE_LEVELS = ["high", "medium", "low"] as const;

export const SORT_OPTIONS = [
  { value: "importedAt", label: "Date Imported" },
  { value: "email_date", label: "Email Date" },
  { value: "dateApplied", label: "Date Applied" },
  { value: "company", label: "Company" },
  { value: "job_title", label: "Job Title" },
  { value: "confidence", label: "Confidence" },
] as const;

/** Display metadata for each confidence level. */
export const CONFIDENCE_META: Record<
  "high" | "medium" | "low",
  {
    label: string;
    color: string;
    bgColor: string;
    dotColor: string;
    sortOrder: number;
  }
> = {
  high: {
    label: "High",
    color: "text-emerald-700",
    bgColor: "bg-emerald-50",
    dotColor: "bg-emerald-500",
    sortOrder: 0,
  },
  medium: {
    label: "Medium",
    color: "text-amber-700",
    bgColor: "bg-amber-50",
    dotColor: "bg-amber-400",
    sortOrder: 1,
  },
  low: {
    label: "Low",
    color: "text-rose-700",
    bgColor: "bg-rose-50",
    dotColor: "bg-rose-400",
    sortOrder: 2,
  },
};

"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { useLiveQuery } from "dexie-react-hooks";
import {
  Briefcase,
  Bookmark,
  Send,
  MessageSquare,
  XCircle,
  Trophy,
  TrendingUp,
  Upload,
  Clock,
} from "lucide-react";
import Link from "next/link";

import { db } from "@/lib/db";
import { STATUS_META } from "@/lib/constants";
import { countBy, topN, timeAgo, formatDate, groupBy } from "@/lib/utils";
import { PageHeader } from "@/components/shell/PageHeader";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { JobRecord } from "@/types";
import { format, parseISO, isValid } from "date-fns";

/**
 * Lazy-load the entire recharts charting section so the ~200 kB recharts
 * bundle is only fetched when the dashboard has data to display.
 */
const DashboardCharts = dynamic(
  () =>
    import("@/components/dashboard/DashboardCharts").then(
      (m) => m.DashboardCharts,
    ),
  {
    loading: () => (
      <section className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="bg-white border border-border rounded-xl p-5 shadow-sm h-[260px] animate-pulse"
          />
        ))}
      </section>
    ),
    ssr: false,
  },
);

/* ── Helper: jobs by day ─────────────────────────────────────────── */
function buildJobsOverTime(
  jobs: JobRecord[],
): Array<{ date: string; count: number }> {
  const grouped = groupBy(jobs, (j) => {
    const raw = j.email_date ?? j.importedAt;
    try {
      const d = parseISO(raw);
      if (isValid(d)) return format(d, "MMM d");
    } catch {
      /* intentionally empty */
    }
    return "Unknown";
  });

  return Object.entries(grouped)
    .map(([date, items]) => ({ date, count: items.length }))
    .slice(-14);
}

/* ── Main component ─────────────────────────────────────────────── */
export default function DashboardPage() {
  const jobs = useLiveQuery(() => db.jobs.toArray(), []);
  const batches = useLiveQuery(
    () => db.importBatches.orderBy("importedAt").reverse().limit(5).toArray(),
    [],
  );

  /**
   * Memoize all derived metrics so they only recompute when the underlying
   * jobs array changes (Dexie returns a new array reference on writes).
   */
  const metrics = useMemo(() => {
    if (!jobs || jobs.length === 0) return null;

    const activeJobs = jobs.filter((j) => !j.archived);
    const total = activeJobs.length;
    const saved = activeJobs.filter((j) => j.saved).length;
    const applied = activeJobs.filter((j) =>
      [
        "applied",
        "oa",
        "recruiter_screen",
        "interview",
        "final_round",
      ].includes(j.applicationStatus),
    ).length;
    const interviewing = activeJobs.filter((j) =>
      ["interview", "final_round"].includes(j.applicationStatus),
    ).length;
    const rejected = activeJobs.filter(
      (j) => j.applicationStatus === "rejected",
    ).length;
    const offers = activeJobs.filter(
      (j) => j.applicationStatus === "offer",
    ).length;

    const statusCounts = countBy(activeJobs, (j) => j.applicationStatus);
    const statusChartData = Object.entries(statusCounts)
      .map(([status, count]) => ({
        name: STATUS_META[status as keyof typeof STATUS_META]?.label ?? status,
        count,
      }))
      .sort((a, b) => b.count - a.count);

    const locationCounts = countBy(
      activeJobs.filter((j) => j.location && j.location.trim()),
      (j) => j.location ?? "Unknown",
    );
    const topLocations = topN(locationCounts, 6);

    const companyCounts = countBy(activeJobs, (j) => j.company ?? "Unknown");
    const topCompanies = topN(companyCounts, 6);

    const jobsOverTime = buildJobsOverTime(activeJobs);

    const now = new Date();
    const followUps = activeJobs
      .filter((j) => j.nextFollowUpDate && new Date(j.nextFollowUpDate) >= now)
      .sort((a, b) =>
        (a.nextFollowUpDate ?? "").localeCompare(b.nextFollowUpDate ?? ""),
      )
      .slice(0, 5);

    const recentJobs = [...activeJobs]
      .sort((a, b) => b.importedAt.localeCompare(a.importedAt))
      .slice(0, 5);

    return {
      total,
      saved,
      applied,
      interviewing,
      rejected,
      offers,
      statusChartData,
      topLocations,
      topCompanies,
      jobsOverTime,
      followUps,
      recentJobs,
    };
  }, [jobs]);

  if (jobs === undefined) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="h-5 w-5 rounded-full border-2 border-violet border-t-transparent animate-spin" />
      </div>
    );
  }

  if (jobs.length === 0 || !metrics) {
    return (
      <div className="flex-1 flex flex-col overflow-auto">
        <PageHeader title="Dashboard" />
        <div className="flex-1 flex items-center justify-center">
          <EmptyState />
        </div>
      </div>
    );
  }

  const {
    total,
    saved,
    applied,
    interviewing,
    rejected,
    offers,
    statusChartData,
    topLocations,
    topCompanies,
    jobsOverTime,
    followUps,
    recentJobs,
  } = metrics;

  return (
    <div className="flex-1 flex flex-col overflow-auto">
      <PageHeader title="Dashboard">
        <Link
          href="/import"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <Upload className="h-4 w-4" />
          Import
        </Link>
      </PageHeader>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* KPI Grid */}
        <section>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
            <KpiCard
              label="Total"
              value={total}
              icon={Briefcase}
              accentColor="#7c3aed"
            />
            <KpiCard
              label="Saved"
              value={saved}
              icon={Bookmark}
              accentColor="#2563eb"
            />
            <KpiCard
              label="Applied"
              value={applied}
              icon={Send}
              accentColor="#4f46e5"
            />
            <KpiCard
              label="Interviewing"
              value={interviewing}
              icon={MessageSquare}
              accentColor="#0284c7"
            />
            <KpiCard
              label="Rejected"
              value={rejected}
              icon={XCircle}
              accentColor="#dc2626"
            />
            <KpiCard
              label="Offers"
              value={offers}
              icon={Trophy}
              accentColor="#059669"
            />
          </div>
        </section>

        {/* Charts — lazy-loaded */}
        <DashboardCharts
          statusChartData={statusChartData}
          jobsOverTime={jobsOverTime}
          topLocations={topLocations}
          topCompanies={topCompanies}
        />

        {/* Bottom row */}
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {/* Recent imports */}
          <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest">
                Recent Imports
              </h3>
              <Link
                href="/jobs"
                className="text-sm text-violet font-medium hover:underline"
              >
                View all
              </Link>
            </div>
            <div className="space-y-1">
              {recentJobs.map((job) => (
                <Link
                  key={job.id}
                  href={`/jobs/${job.id}`}
                  className="flex items-center gap-3 px-2 py-2.5 rounded-lg hover:bg-surface-3 transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-text-primary truncate">
                      {job.job_title}
                    </p>
                    <p className="text-sm text-text-tertiary truncate">
                      {job.company}
                      {job.location ? ` · ${job.location}` : ""}
                    </p>
                  </div>
                  <StatusBadge status={job.applicationStatus} showDot={false} />
                  <span className="text-xs text-text-tertiary shrink-0">
                    {timeAgo(job.email_date ?? job.importedAt)}
                  </span>
                </Link>
              ))}
            </div>
          </div>

          {/* Follow-ups & batches */}
          <div className="space-y-5">
            {/* Upcoming follow-ups */}
            <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
              <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest mb-4">
                Upcoming Follow-Ups
              </h3>
              {followUps.length === 0 ? (
                <p className="text-sm text-text-tertiary">
                  No follow-ups scheduled.
                </p>
              ) : (
                <div className="space-y-1">
                  {followUps.map((job) => (
                    <Link
                      key={job.id}
                      href={`/jobs/${job.id}`}
                      className="flex items-center gap-3 px-2 py-2.5 rounded-lg hover:bg-surface-3 transition-colors"
                    >
                      <Clock className="h-4 w-4 text-amber-500 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-text-primary truncate">
                          {job.job_title} at {job.company}
                        </p>
                      </div>
                      <span className="text-xs text-amber-600 shrink-0 font-medium">
                        {formatDate(job.nextFollowUpDate)}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Recent batches */}
            <div className="bg-white border border-border rounded-xl p-5 shadow-sm">
              <h3 className="text-xs font-bold text-text-tertiary uppercase tracking-widest mb-4">
                Import History
              </h3>
              {!batches || batches.length === 0 ? (
                <p className="text-sm text-text-tertiary">No imports yet.</p>
              ) : (
                <div className="space-y-2">
                  {batches.map((batch) => (
                    <div
                      key={batch.batchId}
                      className="flex items-center gap-3 text-sm"
                    >
                      <TrendingUp className="h-4 w-4 text-violet shrink-0" />
                      <span className="text-text-secondary flex-1 truncate">
                        {batch.sources.join(", ")}
                      </span>
                      <span className="text-emerald-600 tabular-nums font-semibold">
                        +{batch.inserted}
                      </span>
                      <span className="text-text-tertiary tabular-nums">
                        {timeAgo(batch.importedAt)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

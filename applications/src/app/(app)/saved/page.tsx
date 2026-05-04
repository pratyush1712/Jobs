"use client";

import { useMemo } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { PageHeader } from "@/components/shell/PageHeader";
import { JobRow } from "@/components/jobs/JobRow";
import { Bookmark } from "lucide-react";

export default function SavedPage() {
  const savedJobs = useLiveQuery(
    () => db.jobs.where("saved").equals(1).toArray(),
    [],
  );

  const sorted = useMemo(() => {
    if (!savedJobs) return [];
    return [...savedJobs].sort((a, b) =>
      b.importedAt.localeCompare(a.importedAt),
    );
  }, [savedJobs]);

  if (savedJobs === undefined) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="h-5 w-5 rounded-full border-2 border-violet border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <PageHeader
        title="Saved"
        description={
          savedJobs.length > 0 ? `${savedJobs.length} jobs` : undefined
        }
      />

      {sorted.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 py-16">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-surface-3">
            <Bookmark className="h-5 w-5 text-text-tertiary" />
          </div>
          <h3 className="text-[15px] font-semibold text-text-primary">
            No saved jobs
          </h3>
          <p className="text-[13px] text-text-tertiary max-w-[260px] text-center leading-relaxed">
            Bookmark jobs you want to revisit later using the save button on any
            row.
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          {sorted.map((job) => (
            <JobRow key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}

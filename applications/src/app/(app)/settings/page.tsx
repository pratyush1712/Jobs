"use client";

import { useState } from "react";
import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { PageHeader } from "@/components/shell/PageHeader";
import { cn, pluralize } from "@/lib/utils";
import { Trash2, Database, AlertTriangle, CheckCircle } from "lucide-react";

export default function SettingsPage() {
  const jobCount = useLiveQuery(() => db.jobs.count(), []);
  const batchCount = useLiveQuery(() => db.importBatches.count(), []);
  const [cleared, setCleared] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function clearAllData() {
    await db.jobs.clear();
    await db.importBatches.clear();
    setCleared(true);
    setConfirming(false);
  }

  return (
    <div className="flex-1 flex flex-col overflow-auto">
      <PageHeader title="Settings" />

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-lg space-y-6">
          {/* Storage info */}
          <section className="bg-surface-2 border border-divider rounded-lg p-4 space-y-3">
            <h2 className="text-[12px] font-semibold text-text-secondary uppercase tracking-wider">
              Local Storage
            </h2>
            <div className="flex items-start gap-3">
              <Database className="h-4 w-4 text-violet mt-0.5 shrink-0" />
              <div className="space-y-1">
                <p className="text-[13px] text-text-primary">
                  {jobCount !== undefined
                    ? pluralize(jobCount, "job record")
                    : "Loading…"}
                </p>
                <p className="text-[12px] text-text-tertiary">
                  {batchCount !== undefined
                    ? `${batchCount} import ${batchCount === 1 ? "batch" : "batches"}`
                    : ""}
                </p>
                <p className="text-[11px] text-text-tertiary mt-2 leading-relaxed">
                  All data is stored locally in your browser via IndexedDB. No
                  data leaves your device.
                </p>
              </div>
            </div>
          </section>

          {/* Danger zone */}
          <section className="bg-rose-950/20 border border-rose-800/30 rounded-lg p-4 space-y-3">
            <h2 className="text-[12px] font-semibold text-rose-400 uppercase tracking-wider">
              Danger Zone
            </h2>

            {cleared ? (
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle className="h-4 w-4" />
                <span className="text-[13px]">All data cleared.</span>
              </div>
            ) : confirming ? (
              <div className="space-y-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-[13px] text-text-secondary">
                    This will permanently delete all job records and import
                    history. This cannot be undone.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={clearAllData}
                    className={cn(
                      "px-3 py-2 rounded-md text-[13px] font-medium",
                      "bg-rose-600 text-white hover:bg-rose-700 transition-colors",
                    )}
                  >
                    Yes, delete everything
                  </button>
                  <button
                    onClick={() => setConfirming(false)}
                    className="px-3 py-2 rounded-md text-[13px] text-text-tertiary hover:text-text-secondary transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[13px] font-medium text-text-primary">
                    Clear all data
                  </p>
                  <p className="text-[12px] text-text-tertiary mt-0.5">
                    Delete all jobs, batches, and settings.
                  </p>
                </div>
                <button
                  onClick={() => setConfirming(true)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 rounded-md",
                    "text-[12px] font-medium",
                    "bg-rose-950/60 text-rose-400 border border-rose-800/40",
                    "hover:bg-rose-950/80 transition-colors",
                  )}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Clear data
                </button>
              </div>
            )}
          </section>

          {/* About */}
          <section className="text-[12px] text-text-tertiary space-y-1">
            <p>Job Tracker — local-first, no server, no sync.</p>
            <p>Built with Next.js, Dexie, Tailwind, and shadcn/ui.</p>
          </section>
        </div>
      </div>
    </div>
  );
}

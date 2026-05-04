/**
 * Dexie (IndexedDB) setup.
 * All app data is stored locally in the browser — no server required.
 */

import Dexie, { type Table } from "dexie";
import type { JobRecord, ImportBatch, AppSettings } from "@/types";

export class JobTrackerDB extends Dexie {
  jobs!: Table<JobRecord, number>;
  importBatches!: Table<ImportBatch, number>;
  settings!: Table<AppSettings, number>;

  constructor() {
    super("JobTrackerDB");

    this.version(1).stores({
      /**
       * jobs:
       *   ++id          — auto-increment primary key
       *   dedupeKey     — unique dedupe identifier (job_url or compound)
       *   company       — for filtering/grouping
       *   job_title     — for searching
       *   location      — for filtering
       *   applicationStatus — for filtering
       *   importedAt    — for sorting
       *   email_date    — for sorting
       *   saved         — boolean filter
       *   archived      — boolean filter
       *   importBatchId — link to batch
       */
      jobs: "++id, &dedupeKey, company, job_title, location, applicationStatus, importedAt, email_date, saved, archived, importBatchId",

      /**
       * importBatches:
       *   ++id          — auto-increment primary key
       *   batchId       — unique batch identifier
       *   importedAt    — for sorting
       */
      importBatches: "++id, &batchId, importedAt",

      /**
       * settings:
       *   ++id          — auto-increment primary key
       *   key           — unique settings key
       */
      settings: "++id, &key",
    });
  }
}

/**
 * Singleton database instance.
 * Exported directly so every import shares the exact same object reference.
 * This is critical — dexie-react-hooks detects table changes by reference
 * equality; a Proxy or factory that returns a new object each call will
 * cause infinite re-render loops.
 */
export const db = new JobTrackerDB();

/** Alias so normalize.ts can call getDb() without changing its code. */
export function getDb(): JobTrackerDB {
  return db;
}

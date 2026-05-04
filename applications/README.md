# Job Tracker Dashboard

A local-first job application tracker with a Linear-inspired product aesthetic.
All data lives in your browser via IndexedDB — no server, no database setup, no migrations.

---

## Stack

| Layer       | Tech                                  |
| ----------- | ------------------------------------- |
| Framework   | Next.js 16 (App Router)               |
| Language    | TypeScript (strict)                   |
| Styling     | Tailwind CSS v4 + shadcn/ui           |
| Persistence | Dexie (IndexedDB) + dexie-react-hooks |
| UI State    | Zustand                               |
| Forms       | React Hook Form + Zod                 |
| Charts      | Recharts                              |
| Upload      | react-dropzone                        |

---

## Getting Started

```bash
# Install dependencies
pnpm install

# Start dev server
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Importing Jobs

1. Navigate to **Import** in the sidebar (or press `⌘K` → Import Jobs).
2. Drag and drop a `.jsonl` or `.json` file onto the drop zone.
3. Review the import preview — records are deduplicated before insert.
4. Click **Import** to persist records to IndexedDB.

### Supported Formats

**JSONL** (recommended) — one JSON object per line:

```jsonl
{"company":"Acme","job_title":"Engineer","location":"SF",...}
{"company":"Corp","job_title":"Developer","location":"Remote",...}
```

**JSON array:**

```json
[
  {"company":"Acme","job_title":"Engineer",...},
  {"company":"Corp","job_title":"Developer",...}
]
```

A sample file is available at `public/sample-jobs.jsonl` — try importing it to see the dashboard populate.

---

## File Structure

```
src/
├── app/
│   ├── layout.tsx              — Root layout (sets dark mode)
│   └── (app)/                  — App shell route group
│       ├── layout.tsx          — AppShell wrapper (sidebar)
│       ├── page.tsx            — Dashboard home
│       ├── jobs/
│       │   ├── page.tsx        — Jobs list (table + split view)
│       │   └── [id]/page.tsx   — Job detail (split layout)
│       ├── saved/page.tsx      — Saved jobs
│       ├── import/page.tsx     — Import flow
│       └── settings/page.tsx   — Settings + data management
│
├── components/
│   ├── shell/
│   │   ├── AppShell.tsx        — App wrapper with sidebar
│   │   ├── Sidebar.tsx         — Navigation sidebar
│   │   └── PageHeader.tsx      — Page header bar
│   ├── dashboard/
│   │   ├── KpiCard.tsx         — Metric summary card
│   │   ├── EmptyState.tsx      — Empty state prompt
│   │   └── ActivityFeed.tsx    — Timeline log
│   ├── jobs/
│   │   ├── JobRow.tsx          — Single job list row
│   │   └── FilterBar.tsx       — Search + filter chips
│   └── ui/
│       ├── StatusBadge.tsx     — Application status chip
│       ├── SkillBadge.tsx      — Skill/keyword chip
│       └── CommandBar.tsx      — ⌘K quick actions
│
├── lib/
│   ├── db.ts                   — Dexie schema + singleton
│   ├── store.ts                — Zustand UI store + filter logic
│   ├── utils.ts                — Date helpers, string utilities
│   ├── constants.ts            — Status meta, colors, filter options
│   └── import/
│       ├── parse.ts            — File → raw records parser
│       └── normalize.ts        — Records → JobRecord + DB insert
│
└── types/
    └── index.ts                — All domain types
```

---

## Data Model

### JobRecord (stored in IndexedDB)

**Imported fields** (from WTTJ email extractor):

- `gmail_link`, `email_date`, `sender`, `subject`
- `job_url`, `company`, `job_title`, `location`
- `remote_policy`, `employment_type`, `seniority`, `compensation`
- `visa_sponsorship`, `summary`
- `keywords[]`, `required_skills[]`, `preferred_skills[]`
- `responsibilities[]`, `requirements[]`, `nice_to_have[]`
- `confidence`, `raw` (original object for debugging)

**App-managed fields**:

- `applicationStatus` — one of: `interested`, `saved`, `applied`, `oa`, `recruiter_screen`, `interview`, `final_round`, `offer`, `rejected`, `archived`
- `saved`, `archived`
- `dateApplied`, `nextFollowUpDate`
- `referral`, `contactName`, `contactEmail`
- `salaryExpectation`, `notes`
- `activityLog[]` — automatic timeline of status changes and manual notes

---

## Keyboard Shortcuts

| Shortcut                 | Action              |
| ------------------------ | ------------------- |
| `⌘K`                     | Open quick actions  |
| `Esc`                    | Close quick actions |
| `⌘Enter` (in note field) | Save note           |

---

## Features

- **Dashboard** — KPI cards, pipeline chart, jobs over time, top locations/companies, follow-up reminders, import history
- **Jobs list** — Full-text search, status filter chips, sort by any field, table and split-pane views, row actions (open job link, Gmail, save)
- **Job detail** — Premium split layout with full job content on the left, application tracking panel on the right, activity log
- **Import** — Drag-and-drop JSONL/JSON, parse preview, deduplication, batch metadata
- **Saved** — Quick view of bookmarked jobs
- **Settings** — Storage stats + data clear option

---

## Design

The dashboard is dark-first with a Linear/Raycast-inspired aesthetic:

- Warm dark neutrals (`oklch` color space)
- Single restrained accent: violet/indigo
- Dense but readable information hierarchy
- Subtle borders, soft panel layering
- Crisp hover/focus states throughout

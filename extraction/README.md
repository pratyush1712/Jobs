# Job Extraction Pipeline

A professional SimplifyJobs + Welcome to the Jungle (WTTJ) extraction pipeline for collecting, deduplicating, resolving, and optionally enriching new-grad job listings.

## Project layout

```text
extraction/
├── main.py                         # Backward-compatible entrypoint
├── run_job_pipeline.py             # Primary pipeline CLI
├── prune_unavailable_jobs.py       # Removes stale WTTJ listings from saved outputs
├── inspect_wttj_apply_modal.py     # Manual WTTJ Apply modal debugger
├── requirements.txt
├── job_pipeline/                   # Reusable pipeline package
├── data/
│   ├── jobs/                       # Generated master outputs and enrichment streams
│   └── cache/                      # Raw upstream/cache JSON files
├── secrets/                        # Local OAuth credentials/tokens (gitignored)
├── artifacts/
│   ├── debug/                      # Playwright/email debug captures
│   └── logs/                       # Ad-hoc text/log dumps
└── runtime/                        # Browser profiles and local runtime state
```

## Setup

```bash
cd extraction
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env  # if you maintain one locally
```

Put Gmail OAuth files in `secrets/`:

```text
secrets/credentials.json
secrets/token.json  # generated after first login if missing
```

You can override these paths with `--credentials-file`, `--token-file`, or `GMAIL_CREDENTIALS_FILE`.

## Run the pipeline

The preferred command is:

```bash
python run_job_pipeline.py
```

`main.py` remains as a compatibility alias:

```bash
python main.py
```

WTTJ browser resolution is enabled by default because WTTJ emails often contain SendGrid tracking links. Disable it only when you intentionally want unresolved WTTJ URLs:

```bash
python run_job_pipeline.py --no-wttj-browser
```

## Common workflows

### Test WTTJ only

```bash
python run_job_pipeline.py \
  --no-simplify \
  --gmail-limit 5 \
  --pause-ms 5000 \
  --no-enrich
```

### Full run without enrichment

```bash
python run_job_pipeline.py \
  --pause-ms 5000 \
  --no-enrich
```

### Full run with Azure OpenAI enrichment

Fill in `.env`:

```env
AZURE_OPENAI_BASE_URL=https://YOUR-RESOURCE-NAME.openai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4.1-mini
AZURE_OPENAI_DEPLOYMENT_BEST=gpt-4.1
```

Then run:

```bash
python run_job_pipeline.py --pause-ms 5000
```

### Include internships temporarily

```bash
python run_job_pipeline.py \
  --no-simplify \
  --gmail-limit 5 \
  --include-wttj-internships \
  --no-enrich
```

### Prune unavailable WTTJ jobs

```bash
python prune_unavailable_jobs.py --dry-run
python prune_unavailable_jobs.py
```

### Inspect one WTTJ Apply modal

```bash
python inspect_wttj_apply_modal.py \
  --url "https://app.welcometothejungle.com/jobs/E5BwXP4B" \
  --company "Mechanize" \
  --title "Junior Software Engineer" \
  --pause-ms 5000 \
  --keep-open
```

## Default generated paths

```text
data/jobs/master_jobs.jsonl
data/jobs/master_jobs.json
data/jobs/master_jobs_errors.jsonl
data/jobs/enrichment_live.jsonl
data/cache/simplify_listings_raw.json
data/cache/wttj_dashboard_links.json
artifacts/debug/wttj_apply/
artifacts/debug/wttj_email/<gmail_id>_link_candidates.json
runtime/wttj_playwright_profile/
```

## WTTJ behavior

WTTJ/Otta emails often wrap job-card links and notification controls in SendGrid `/ls/click` URLs. The pipeline rejects obvious notification/settings/unsubscribe links, keeps SendGrid links when nearby context looks like a real job card, lets Playwright follow the redirect to WTTJ, clicks **Apply**, and extracts the external ATS/company application URL.

Internship/co-op/apprenticeship matches are filtered per job card before Playwright and enrichment so one mixed email can still produce valid full-time records.

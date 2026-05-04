## Learned User Preferences

- Always use double quotes for strings; never single quotes in Python or TypeScript.
- Use word-boundary regexes (`\b`) for keyword matching — never simple substring `in` checks — to prevent false positives like "intern" matching "internal".
- Add `--dry-run` flags to any script that modifies or deletes data files, and remind the user to run dry-run first.
- Do not use TypeScript `any`, non-null assertion (`!`), or `as unknown as T` casts.
- User cannot work at defense contractors or companies requiring US citizenship/security clearance (Anduril, etc.); filter them from all job sources.
- User is a new-grad software engineer seeking sponsorship-friendly roles; treat "new_grad" / "New Grad" seniority as a key filter.
- Prefer `--limit N` / `--enrich-limit N` flags for smoke-testing expensive API calls before full runs.
- Write full code with no placeholders; include clear inline comments explaining non-obvious logic.

## Learned Workspace Facts

- Workspace root: `/Users/praty/Desktop/personal-tools/grad-plans/WTTJ-Jobs/`; extraction pipeline lives in `extraction/`, TypeScript web app in `applications/`.
- Primary data stores: `extraction/master_jobs.jsonl` (append-only JSONL) and `extraction/master_jobs.json` (JSON array mirror).
- Main pipeline entrypoint: `extraction/run_job_pipeline.py`; orchestration of WTTJ email processing in `extraction/unified_job_master.py`.
- Key pipeline modules: `job_pipeline/wttj_email.py` (email parsing), `job_pipeline/wttj_resolver.py` (Playwright browser resolver), `job_pipeline/constants.py` (all selectors/constants), `job_pipeline/enrichment_worker.py` (Azure OpenAI enrichment), `job_pipeline/simplify.py` (SimplifyJobs source), `job_pipeline/dedupe.py` (deduplication).
- LLM enrichment uses Azure OpenAI; credentials live in `extraction/.env` (never commit this file).
- WTTJ Playwright browser uses a persistent profile at `.wttj-playwright-profile` — separate from the user's regular Chrome; user must log in inside the Playwright window at least once.
- When logged in to WTTJ, the Apply button is absent from the DOM; the authenticated path is `page.keyboard.press("a")`. The reliable login indicator is `[data-testid="save-button"]`.
- SimplifyJobs defense contractors set `sponsorship: "Other"` — catch them via `BLOCKED_COMPANIES` list in `constants.py`, not the sponsorship value alone.
- GitHub Actions workflow at `.github/workflows/enrich.yml` runs enrichment in the cloud; secrets are passed via `env:` map (not heredoc) to handle special characters safely.
- Scripts can be run from the repo root (not just `extraction/`) because `run_job_pipeline.py` uses `__file__`-relative path resolution for `.env` and data dirs.
- `extraction/dump_emails.py` cross-references Gmail emails against `master_jobs.jsonl` for debugging parse quality; `extraction/prune_unavailable_wttj.py` removes stale WTTJ listings.

# Resume Tailor Pipeline

Automatically tailors your LaTeX resume for every job in `enrichment_live.jsonl`
using Azure OpenAI, with a 5-stage agentic pipeline.

## Project Structure

```
resume-tailor/
├── main.py              # Entry point + CLI
├── config.py            # Paths, model settings, dotenv loader
├── pipeline.py          # 5-stage orchestrator
├── prompts.py           # All LLM prompts (stage functions)
├── llm_client.py        # Azure OpenAI wrapper with tenacity retry
├── readme_loader.py     # Loads readmes/ context files
├── resume_selector.py   # Picks base .tex + past company resumes
├── job_context.py       # Formats a job dict → clean JD block
├── state.py             # Tracks processed jobs (idempotent re-runs)
└── requirements.txt
```

## Setup

### 1 — Install dependencies

```bash
pip install -r resume-tailor/requirements.txt
```

### 2 — Configure credentials

The pipeline reuses `extraction/.env` — no extra setup needed if the
extraction pipeline already works. The required keys are:

```dotenv
# extraction/.env (already needed by the extraction pipeline)
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/

# Deployments shared with the extraction pipeline
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini   # stages 3 & 5 by default
AZURE_OPENAI_DEPLOYMENT_BEST=gpt-4o        # stages 1 & 2 by default
```

#### Optional resume-tailor overrides

Set these in `extraction/.env` or your shell to use different deployments
for the resume pipeline without touching the extraction pipeline:

```dotenv
# Use a high-quality reasoning model for analysis stages (1 & 2)
RESUME_TAILOR_DEPLOYMENT_REASONING=o4-mini

# Use a faster/cheaper model for execution stages (3 & 5)
RESUME_TAILOR_DEPLOYMENT_FAST=gpt-4o-mini

# Set to empty string to omit temperature (required for o-series models)
RESUME_TAILOR_TEMPERATURE_REASONING=

# Request settings
RESUME_TAILOR_MAX_RETRIES=3
RESUME_TAILOR_REQUEST_TIMEOUT_S=120
```

## Usage

```bash
# Process all "interested" jobs
python resume-tailor/main.py

# Process only 3 jobs (smoke-test before full run)
python resume-tailor/main.py --limit 3

# Process a specific job by ID
python resume-tailor/main.py --job-id cd218df1-f792-49c8-a221-64af3ff15f82

# Reprocess jobs even if output already exists
python resume-tailor/main.py --no-skip

# Filter by a different status
python resume-tailor/main.py --status applied
```

## Pipeline Stages

| Stage                  | LLM tier          | Purpose                                                                |
| ---------------------- | ----------------- | ---------------------------------------------------------------------- |
| 1 — Keyword Extraction | `reasoning=True`  | Deep JD analysis vs your background — finds gaps, flags dishonest adds |
| 2 — Rewrite Plan       | `reasoning=True`  | Line-by-line LaTeX change plan with reasons                            |
| 3 — LaTeX Rewrite      | `reasoning=False` | Applies the plan; outputs a complete `.tex` file                       |
| 5 — ATS Self-Check     | `reasoning=False` | Validates output; produces ATS score (0–100)                           |

`reasoning=True` → `MODEL_REASONING` (defaults to `AZURE_OPENAI_DEPLOYMENT_BEST`)
`reasoning=False` → `MODEL_FAST` (defaults to `AZURE_OPENAI_DEPLOYMENT_FAST`)

## Model Flexibility

Switching models is purely config — no code changes:

| Scenario                     | What to set                                                                                              |
| ---------------------------- | -------------------------------------------------------------------------------------------------------- |
| Use GPT-4o for all stages    | Set both `RESUME_TAILOR_DEPLOYMENT_REASONING` and `RESUME_TAILOR_DEPLOYMENT_FAST` to the same deployment |
| Use o4-mini for analysis     | Set `RESUME_TAILOR_DEPLOYMENT_REASONING=o4-mini` and `RESUME_TAILOR_TEMPERATURE_REASONING=` (empty)      |
| Use gpt-4.1 as the fast tier | Set `RESUME_TAILOR_DEPLOYMENT_FAST=gpt-4.1`                                                              |

## Output Layout

```
output/
├── resumes/
│   └── Company__Role__jobid8/
│       └── resume_Company__Role__jobid8.tex   ← tailored resume
├── logs/
│   └── Company__Role__jobid8/
│       ├── stage1_keywords.md     ← keyword gap table
│       ├── stage2_plan.md         ← per-line rewrite plan
│       └── stage5_ats_check.md    ← ATS score + suggestions
├── state.json                     ← processed job registry
└── summary.json                   ← last run summary
```

## Tips

- Use `--limit 1` first to validate credentials and model settings before a full run.
- The `state.json` prevents re-processing on subsequent runs — delete it or use `--no-skip` to redo.
- Compile output `.tex` files with `pdflatex` or `xelatex`.
- Stage logs show exactly what changed and why — review `stage2_plan.md` to audit edits.

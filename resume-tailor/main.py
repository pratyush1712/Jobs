"""
Resume Tailor — main entry point.

Usage:
    python main.py                         # process all interested jobs
    python main.py --status interested     # filter by status
    python main.py --job-id <uuid>         # process single job
    python main.py --limit 5               # cap at N jobs
    python main.py --no-skip               # reprocess already-done jobs
"""

import argparse
import json
import logging
import traceback

from config import (
    JOBS_JSON,
    LOGS_DIR,
    MAX_JOBS,
    OUTPUT_DIR,
    SKIP_EXISTING,
    TARGET_STATUSES,
)
from pipeline import run_pipeline
from readme_loader import load_readmes
from state import is_processed, load_state, mark_processed, save_state
from utils import jsonl_reader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "run.log" if LOGS_DIR.exists() else "run.log"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--status", default=None, help="Filter by application_status")
    p.add_argument("--job-id", default=None, help="Process a single job by ID")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--no-skip", action="store_true", help="Reprocess already done jobs")
    return p.parse_args()


def main():
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    jobs = list(jsonl_reader(JOBS_JSON))
    readme_context = load_readmes()
    state = load_state()

    # ── Filters ────────────────────────────────────────────────────────────
    if args.job_id:
        jobs = [j for j in jobs if j.get("id") == args.job_id]
    else:
        target_statuses = {args.status} if args.status else TARGET_STATUSES
        jobs = [j for j in jobs if j.get("application_status") in target_statuses]
        jobs = [j for j in jobs if j.get("active", True)]

    skip = SKIP_EXISTING and not args.no_skip
    if skip:
        jobs = [j for j in jobs if not is_processed(state, j.get("id", ""))]

    limit = args.limit or MAX_JOBS
    if limit:
        jobs = jobs[:limit]

    logger.info(f"Processing {len(jobs)} job(s)...")

    results = []
    for i, job in enumerate(jobs, 1):
        jid = job.get("id", "unknown")
        logger.info(
            f"─── [{i}/{len(jobs)}] {job.get('company')} — {job.get('job_title')} ───"
        )
        try:
            result = run_pipeline(job, readme_context)
            mark_processed(state, jid, result)
            save_state(state)
            results.append({"status": "ok", **result})
            logger.info(f"✅  ATS Score: {result['ats_score']} | {result['tex_path']}")
        except Exception as e:
            logger.error(f"❌  Failed: {jid} — {e}")
            logger.debug(traceback.format_exc())
            results.append({"status": "error", "job_id": jid, "error": str(e)})

    # ── Summary ────────────────────────────────────────────────────────────
    ok = [r for r in results if r["status"] == "ok"]
    err = [r for r in results if r["status"] == "error"]
    scores = [r["ats_score"] for r in ok if r.get("ats_score")]

    logger.info("═" * 60)
    logger.info(f"Done. ✅ {len(ok)} succeeded | ❌ {len(err)} failed")
    if scores:
        logger.info(
            f"ATS Scores — avg: {sum(scores) / len(scores):.0f} | min: {min(scores)} | max: {max(scores)}"
        )
    logger.info(f"Output directory: {OUTPUT_DIR}")

    # Write summary JSON
    summary_path = OUTPUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info(f"Summary written: {summary_path}")


if __name__ == "__main__":
    main()

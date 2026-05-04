#!/usr/bin/env python3
"""Re-enrich a single job record using raw description text.

Use this when the enrichment pipeline fetched a generic careers-portal shell
instead of the actual job description, leaving the record without keywords,
tech stack, or responsibilities.

WORKFLOW
--------
1. Identify the target record via --url (matches job_url or wttj_job_url).
2. Supply the job description text via --description-file FILE or stdin.
3. Run with --dry-run first to confirm the right record is found.
4. Run without --dry-run to patch the record in master_jobs.jsonl/json.

EXAMPLES
--------
# Dry run — confirm the right record is found:
python extraction/re_enrich_with_text.py \\
    --url "https://jobs.slice.com/..." \\
    --description-file /tmp/slice_jd.txt \\
    --dry-run

# Apply — patch the record and re-enrich:
python extraction/re_enrich_with_text.py \\
    --url "https://jobs.slice.com/..." \\
    --description-file /tmp/slice_jd.txt

# Pipe description from clipboard / stdin:
pbpaste | python extraction/re_enrich_with_text.py \\
    --url "https://jobs.slice.com/..."
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Resolve extraction/ directory so job_pipeline can be imported from any cwd.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from job_pipeline.colors import bold, dim, err, ok, warn
from job_pipeline.constants import (
    DEFAULT_MASTER_JSON,
    DEFAULT_MASTER_JSONL,
    EXTRACTION_DIR,
)
from job_pipeline.enrichment_pipeline import enrich_records
from job_pipeline.models import coerce_master_record
from job_pipeline.utils import load_jsonl, write_json


def load_dotenv_light(path: Path = EXTRACTION_DIR / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        import os

        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Re-enrich a single job record with supplied raw description text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--url",
        required=True,
        metavar="JOB_URL",
        help="job_url or wttj_job_url of the target record (substring match).",
    )
    p.add_argument(
        "--description-file",
        metavar="FILE",
        help="Path to a text file containing the raw job description. "
        "If omitted, the description is read from stdin.",
    )
    p.add_argument(
        "--master-jsonl",
        default=DEFAULT_MASTER_JSONL,
        metavar="PATH",
        help="Path to master_jobs.jsonl (default: %(default)s).",
    )
    p.add_argument(
        "--master-json",
        default=DEFAULT_MASTER_JSON,
        metavar="PATH",
        help="Path to master_jobs.json (default: %(default)s).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print which record would be patched without writing any files.",
    )
    return p.parse_args()


def _find_record_index(records: list[dict[str, Any]], url_fragment: str) -> int:
    """Return the index of the first record whose job_url or wttj_job_url
    contains url_fragment (case-insensitive).  Returns -1 if not found."""
    frag = url_fragment.lower()
    for i, r in enumerate(records):
        job_url = (r.get("job_url") or "").lower()
        wttj_url = (
            r.get("wttj_job_url") or r.get("raw_listing", {}).get("wttj_job_url") or ""
        ).lower()
        if frag in job_url or frag in wttj_url:
            return i
    return -1


def main() -> None:
    load_dotenv_light()
    args = parse_args()

    # --- Read description text from file or stdin ---
    if args.description_file:
        desc_text = Path(args.description_file).read_text(encoding="utf-8").strip()
    else:
        if sys.stdin.isatty():
            print(
                warn(
                    "No --description-file given. Paste the job description below, "
                    "then press Ctrl-D (macOS/Linux) or Ctrl-Z + Enter (Windows):"
                ),
                flush=True,
            )
        desc_text = sys.stdin.read().strip()

    if not desc_text:
        print(err("✗  Description text is empty. Aborting."), flush=True)
        sys.exit(1)

    # --- Load master records ---
    jsonl_path = Path(args.master_jsonl)
    json_path = Path(args.master_json)

    if not jsonl_path.exists():
        print(err(f"✗  master_jobs.jsonl not found: {jsonl_path}"), flush=True)
        sys.exit(1)

    records: list[dict[str, Any]] = load_jsonl(jsonl_path)
    print(dim(f"  Loaded {len(records):,} records from {jsonl_path}"), flush=True)

    # --- Find the target record ---
    idx = _find_record_index(records, args.url)
    if idx == -1:
        print(err(f"✗  No record matched URL fragment: {args.url!r}"), flush=True)
        print(
            dim("  Tip: pass a shorter substring of the URL, e.g. the job ID portion."),
            flush=True,
        )
        sys.exit(1)

    target = records[idx]
    company = target.get("company") or "?"
    title = target.get("job_title") or "?"
    job_url = target.get("job_url") or "(no URL)"
    print(
        bold("  Target record:") + f"  {company} — {title}\n  {dim('url:')} {job_url}",
        flush=True,
    )

    if args.dry_run:
        print(
            ok(
                "\n  --dry-run: record found. No files written.\n"
                "  Re-run without --dry-run to apply the patch."
            ),
            flush=True,
        )
        sys.exit(0)

    # --- Patch: attach raw_description and clear stale enrichment fields ---
    # Clearing keywords / required_skills makes enrich_records consider this
    # record unenriched and eligible for a fresh LLM pass.
    patched = dict(target)
    patched["raw_description"] = desc_text
    patched.pop("keywords", None)
    patched.pop("required_skills", None)
    patched.pop("tech_stack", None)
    patched.pop("responsibilities", None)
    patched.pop("summary", None)
    patched.pop("confidence", None)
    # Also clear the enrichment_error flag so the progress tracker doesn't
    # report it as a stale failure.
    if isinstance(patched.get("raw_listing"), dict):
        patched["raw_listing"].pop("enrichment_error", None)

    records[idx] = patched

    # --- Run enrichment on only this record ---
    print(bold("\n  Running enrichment on patched record..."), flush=True)
    enriched_records = enrich_records(records, limit=None)

    # Strip raw_description from the final record — it's a transient input
    # field, not something we want stored permanently in the master data.
    result = enriched_records[idx]
    result.pop("raw_description", None)
    enriched_records[idx] = result

    # --- Write back ---
    final = [coerce_master_record(r) for r in enriched_records]

    tmp_jsonl = jsonl_path.with_suffix(".jsonl.tmp")
    tmp_json = json_path.with_suffix(".json.tmp")

    with tmp_jsonl.open("w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_json(tmp_json, final, pretty=True)

    tmp_jsonl.replace(jsonl_path)
    tmp_json.replace(json_path)

    enriched = enriched_records[idx]
    conf = enriched.get("confidence", "?")
    tech = enriched.get("tech_stack", [])
    skills = enriched.get("required_skills", [])

    print(
        ok("\n  ✓ Done.")
        + dim(
            f"  confidence={conf}  "
            f"tech_stack={len(tech)}  required_skills={len(skills)}"
        ),
        flush=True,
    )
    print(dim(f"  Written → {jsonl_path}"), flush=True)


if __name__ == "__main__":
    main()

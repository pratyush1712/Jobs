"""
prune_unavailable_jobs.py
--------------------------
Visit every WTTJ job record in data/jobs/master_jobs.jsonl with a real browser and remove
entries where the WTTJ job page now shows "Job no longer available".

If a SendGrid tracking URL redirects to a different final WTTJ URL, the record's
``wttj_dashboard_url`` is updated to the clean redirected URL (no query params).

Usage
-----
    # Dry-run — preview what would be removed, touch nothing:
    python prune_unavailable_jobs.py --dry-run

    # Live run — prune and overwrite data/jobs/master_jobs.jsonl:
    python prune_unavailable_jobs.py

    # Headless (no visible browser window):
    python prune_unavailable_jobs.py --headless

    # Adjust pause between page load and availability check (ms):
    python prune_unavailable_jobs.py --pause-ms 3000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: make sure the extraction/ directory is on sys.path so that
# ``job_pipeline`` can be imported regardless of where the script is run from.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from job_pipeline.utils import is_sendgrid_tracking_url, is_wttj_job_detail_url, write_json
from job_pipeline.wttj_resolver import (
    WTTJBrowserResolver,
    detect_job_unavailable,
    detect_job_unavailable_in_html,
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_MASTER_JSONL = _HERE / "data/jobs/master_jobs.jsonl"
_DEFAULT_MASTER_JSON  = _HERE / "data/jobs/master_jobs.json"
_DEFAULT_PAUSE_MS     = 4000


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load a .env file from the extraction directory, if present."""
    env_path = _HERE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Return all valid JSON-object lines from *path*."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            pass
    return rows


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write *records* as newline-delimited JSON to *path* atomically."""
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# URL selection
# ---------------------------------------------------------------------------

def _best_wttj_url(record: dict[str, Any]) -> str:
    """Return the best URL to check for job availability.

    Preference order:
    1. ``wttj_dashboard_url`` — either a direct WTTJ job URL *or* a SendGrid
       tracking link that the browser will follow to the real WTTJ page.
    2. ``job_url`` — if it points directly to WTTJ.
    3. ``raw_listing.wttj_job_url`` — legacy field.

    SendGrid links are accepted because Playwright follows the redirect
    automatically, landing on the actual WTTJ job detail page.
    """
    dashboard = (record.get("wttj_dashboard_url") or "").strip()
    if dashboard and (is_wttj_job_detail_url(dashboard) or is_sendgrid_tracking_url(dashboard)):
        return dashboard

    job_url = (record.get("job_url") or "").strip()
    if job_url and is_wttj_job_detail_url(job_url):
        return job_url

    raw = record.get("raw_listing") or {}
    raw_wttj = (raw.get("wttj_job_url") or "").strip() if isinstance(raw, dict) else ""
    if raw_wttj and (is_wttj_job_detail_url(raw_wttj) or is_sendgrid_tracking_url(raw_wttj)):
        return raw_wttj

    return ""


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def check_unavailable(
    page: Any,
    url: str,
    pause_ms: int,
) -> tuple[bool, str]:
    """Navigate to *url* and return ``(unavailable, final_url)``.

    *final_url* is the URL the browser settled on after all redirects (e.g.
    SendGrid → WTTJ). It is returned so callers can update the stored record.

    The function returns ``(False, final_url)`` without marking unavailable when:
    - the page raises a navigation error (treated as "can't confirm — keep")
    - the final URL is not a WTTJ job detail page (redirect went somewhere else)
    """
    import time

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        time.sleep(max(pause_ms, 0) / 1000)
    except Exception as nav_err:
        print(f"            [ERR] Navigation failed: {nav_err}")
        return False, url

    final_url: str = page.url
    if final_url != url:
        print(f"            ↳ redirected to: {final_url[:90]}")

    if not is_wttj_job_detail_url(final_url):
        print(f"            [WARN] Final URL is not a WTTJ job page — keeping record.")
        return False, final_url

    # Two-stage check: Playwright selectors first, raw HTML fallback second.
    if detect_job_unavailable(page):
        return True, final_url

    try:
        html = page.content()
        if detect_job_unavailable_in_html(html):
            return True, final_url
    except Exception:
        pass

    return False, final_url


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _load_dotenv()

    parser = argparse.ArgumentParser(
        description="Remove unavailable WTTJ jobs from data/jobs/master_jobs.jsonl.",
    )
    parser.add_argument(
        "--master-jsonl",
        default=str(_DEFAULT_MASTER_JSONL),
        help="Path to data/jobs/master_jobs.jsonl (default: %(default)s)",
    )
    parser.add_argument(
        "--master-json",
        default=str(_DEFAULT_MASTER_JSON),
        help="Path to data/jobs/master_jobs.json — updated in sync if it exists (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without touching files.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Playwright in headless mode (no visible browser window).",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=_DEFAULT_PAUSE_MS,
        help="Milliseconds to wait after page load before checking (default: %(default)s).",
    )
    args = parser.parse_args()

    jsonl_path = Path(args.master_jsonl)
    json_path  = Path(args.master_json)

    all_records = _load_jsonl(jsonl_path)
    if not all_records:
        print(f"No records found in {jsonl_path}. Nothing to do.")
        return

    wttj_records   = [r for r in all_records if r.get("source") == "wttj_gmail"]
    other_records  = [r for r in all_records if r.get("source") != "wttj_gmail"]

    checkable   = [(i, r, _best_wttj_url(r)) for i, r in enumerate(all_records) if r.get("source") == "wttj_gmail" and _best_wttj_url(r)]
    uncheckable = [r for r in wttj_records if not _best_wttj_url(r)]

    print(f"Loaded {len(all_records)} records total.")
    print(f"  WTTJ records  : {len(wttj_records)}")
    print(f"  Checkable     : {len(checkable)}")
    print(f"  Uncheckable   : {len(uncheckable)}  (no usable WTTJ or SendGrid URL)")
    print(f"  Other sources : {len(other_records)}")
    if args.dry_run:
        print("[DRY-RUN] No files will be modified.\n")

    removed: list[dict[str, Any]] = []
    # Map original index → (keep: bool, updated_record)
    verdict: dict[int, tuple[bool, dict[str, Any]]] = {}

    with WTTJBrowserResolver(headless=args.headless, pause_ms=args.pause_ms) as resolver:
        page = resolver._ctx.new_page()  # type: ignore[union-attr]
        try:
            for position, (orig_idx, record, url) in enumerate(checkable, start=1):
                company = record.get("company", "")
                title   = record.get("job_title", "")
                print(
                    f"  [{position:>2}/{len(checkable)}] {company} — {title}\n"
                    f"            URL: {url[:80]}"
                )

                unavailable, resolved_url = check_unavailable(page, url, args.pause_ms)

                updated_record = dict(record)

                # If the redirect landed on a cleaner WTTJ URL, persist it.
                if resolved_url and resolved_url != url and is_wttj_job_detail_url(resolved_url):
                    clean = resolved_url.split("?")[0]
                    if clean != (updated_record.get("wttj_dashboard_url") or "").split("?")[0]:
                        updated_record["wttj_dashboard_url"] = clean
                        print(f"            ↳ updated wttj_dashboard_url → {clean}")

                if unavailable:
                    print(f"            [REMOVE] Job no longer available.")
                    removed.append(record)
                    verdict[orig_idx] = (False, updated_record)
                else:
                    print(f"            [KEEP]")
                    verdict[orig_idx] = (True, updated_record)
        finally:
            page.close()

    # Build final record list in the original order.
    final_records: list[dict[str, Any]] = []
    for idx, record in enumerate(all_records):
        if idx in verdict:
            keep, updated = verdict[idx]
            if keep:
                final_records.append(updated)
        else:
            # Non-WTTJ record or uncheckable WTTJ record — always keep as-is.
            final_records.append(record)

    print(f"\n--- Summary ---")
    print(f"  Records before : {len(all_records)}")
    print(f"  Removed        : {len(removed)}")
    print(f"  Records after  : {len(final_records)}")

    if removed:
        print("\nRemoved jobs:")
        for r in removed:
            print(f"  - {r.get('company', '?')} — {r.get('job_title', '?')}")

    if args.dry_run:
        print("\n[DRY-RUN] Skipping file writes.")
        return

    if not removed:
        print("\nNothing removed — data/jobs/master_jobs.jsonl unchanged.")
        return

    _write_jsonl(jsonl_path, final_records)
    print(f"\nWrote {len(final_records)} records → {jsonl_path}")

    if json_path.exists():
        write_json(json_path, final_records, pretty=True)
        print(f"Wrote {len(final_records)} records → {json_path}")


if __name__ == "__main__":
    main()

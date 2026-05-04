#!/usr/bin/env python3
"""Unified Simplify + WTTJ job pipeline.

WTTJ emails can contain multiple job cards. Internship matches are skipped
per job before browser modal resolution or OpenAI enrichment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure the extraction/ directory is on sys.path so `job_pipeline` can be
# imported regardless of the current working directory (repo root, CI, etc.).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from job_pipeline.colors import bold, bright_white, cyan, dim, err, ok, warn
from job_pipeline.constants import (
    DEFAULT_ERROR_JSONL,
    DEFAULT_FAILED_ENRICHMENT_JSONL,
    DEFAULT_GMAIL_TOKEN_FILE,
    DEFAULT_LOGIN_WAIT_TIMEOUT_S,
    DEFAULT_MASTER_JSON,
    DEFAULT_MASTER_JSONL,
    DEFAULT_RAW_SIMPLIFY,
    DEFAULT_WTTJ_CACHE,
    DEFAULT_WTTJ_DEBUG_DIR,
    DEFAULT_WTTJ_PROFILE_DIR,
    EXTRACTION_DIR,
)
from job_pipeline.dedupe import DedupeIndex
from job_pipeline.enrichment_pipeline import enrich_records
from job_pipeline.enrichment_worker import EnrichConfig
from job_pipeline.models import coerce_master_record
from job_pipeline.simplify import build_simplify_records
from job_pipeline.utils import (
    append_jsonl,
    is_wttj_job_detail_url,
    load_jsonl,
    read_json,
    sort_records_newest_first,
    write_json,
)
from job_pipeline.wttj_email import (
    extract_wttj_job_matches_from_email,
    fetch_wttj_email_records,
    wttj_email_to_master_record,
)
from job_pipeline.wttj_resolver import WTTJBrowserResolver


def load_dotenv_light(path: str | Path = EXTRACTION_DIR / ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified job aggregation pipeline")
    p.add_argument("--no-simplify", action="store_true")
    p.add_argument("--no-gmail", action="store_true")
    p.add_argument("--no-enrich", action="store_true")
    p.add_argument(
        "--enrich-limit",
        type=int,
        default=None,
        metavar="N",
        help="Only enrich the first N unenriched records. Useful for smoke-testing before a full run.",
    )
    p.add_argument("--gmail-limit", type=int, default=None)
    p.add_argument("--credentials-file", default=None)
    p.add_argument("--token-file", default=DEFAULT_GMAIL_TOKEN_FILE)
    # Browser modal resolution is ON by default because WTTJ emails commonly
    # contain SendGrid tracking links, and the real ATS/company URL is usually
    # revealed only after opening the WTTJ job page and clicking Apply.
    p.add_argument(
        "--wttj-browser",
        action="store_true",
        dest="wttj_browser",
        default=True,
        help="Deprecated/no-op: WTTJ browser modal resolution is enabled by default",
    )
    p.add_argument(
        "--no-wttj-browser",
        action="store_false",
        dest="wttj_browser",
        help="Disable Playwright WTTJ Apply modal resolution",
    )
    p.add_argument("--headless", action="store_true")
    p.add_argument("--pause-ms", type=int, default=2000)
    p.add_argument("--wttj-user-data-dir", default=DEFAULT_WTTJ_PROFILE_DIR)
    p.add_argument(
        "--include-wttj-internships",
        action="store_true",
        help="Disable WTTJ internship skip filter",
    )
    p.add_argument("--master-jsonl", default=DEFAULT_MASTER_JSONL)
    p.add_argument("--master-json", default=DEFAULT_MASTER_JSON)
    p.add_argument("--wttj-cache", default=DEFAULT_WTTJ_CACHE)
    p.add_argument("--simplify-raw", default=DEFAULT_RAW_SIMPLIFY)
    p.add_argument("--debug-dir", default=DEFAULT_WTTJ_DEBUG_DIR)
    p.add_argument("--error-jsonl", default=DEFAULT_ERROR_JSONL)
    p.add_argument(
        "--failed-jsonl",
        default=DEFAULT_FAILED_ENRICHMENT_JSONL,
        metavar="PATH",
        help=(
            "JSONL file that receives records whose page fetch or LLM enrichment "
            "failed entirely. These records are excluded from the master output. "
            f"Default: {DEFAULT_FAILED_ENRICHMENT_JSONL}"
        ),
    )
    return p.parse_args()


def stream(path: str, record: dict[str, Any]) -> None:
    append_jsonl(path, coerce_master_record(record))


def _cache_get(cache: dict[str, Any], key: str) -> tuple[str, str]:
    """Return ``(ats_url, wttj_url)`` stored under *key* in the resolve cache.

    Handles both formats:
    - Legacy string format ``{key: "ats_url"}``      → ``("ats_url", "")``
    - New dict format  ``{key: {"ats_url": …, "wttj_url": …}}`` → both values
    """
    entry = cache.get(key)
    if entry is None:
        return ("", "")
    if isinstance(entry, str):
        # Legacy: only the ATS URL was stored, no WTTJ URL available.
        return (entry, "")
    if isinstance(entry, dict):
        return (entry.get("ats_url", ""), entry.get("wttj_url", ""))
    return ("", "")


def _cache_set(
    cache: dict[str, Any],
    sendgrid_key: str,
    ats_url: str,
    wttj_url: str,
) -> None:
    """Write both the ATS URL and resolved WTTJ URL into the resolve cache.

    Stores a dict so that subsequent cache hits can recover *both* the
    permanent WTTJ job URL (used for ``wttj_dashboard_url``) *and* the
    external ATS apply URL (used for ``job_url``).

    Also indexes under the WTTJ URL so that a run starting from a direct
    WTTJ URL still benefits from the cached ATS URL.
    """
    entry: dict[str, str] = {"ats_url": ats_url, "wttj_url": wttj_url}
    cache[sendgrid_key] = entry
    if wttj_url and wttj_url != sendgrid_key:
        cache[wttj_url] = entry


def process_simplify(
    args: argparse.Namespace, dedupe: DedupeIndex, records: list[dict[str, Any]]
) -> None:
    print(bold("Fetching SimplifyJobs listings..."), flush=True)
    simplify_records = build_simplify_records(args.simplify_raw)
    for i, record in enumerate(simplify_records, 1):
        if dedupe.add(record):
            records.append(record)
            stream(args.master_jsonl, record)
        if i % 50 == 0:
            print(dim(f"  Simplify: {i}/{len(simplify_records)} processed"), flush=True)
    print(ok(f"  ✓ SimplifyJobs done — {len(records)} records collected"), flush=True)


def process_wttj(
    args: argparse.Namespace, dedupe: DedupeIndex, records: list[dict[str, Any]]
) -> None:
    print(bold("Fetching WTTJ Gmail messages..."), flush=True)
    email_records, email_stats = fetch_wttj_email_records(
        credentials_file=args.credentials_file,
        token_file=args.token_file,
        limit=args.gmail_limit,
    )
    stats = {
        **email_stats,
        "job_links_found": 0,
        "job_matches_kept": 0,
        "job_matches_skipped_internship": 0,
        "records_written": 0,
    }
    cache: dict[str, Any] = read_json(args.wttj_cache, default={}) or {}

    resolver_cm = None
    resolver = None
    if args.wttj_browser:
        print(
            cyan(
                "  ● Browser resolver ON — Playwright will click Apply to extract ATS URLs."
            ),
            flush=True,
        )
        # In headless mode there is no GUI to log in, so skip the login wait
        # entirely (login_wait_s=0).  The browser can still detect unavailable
        # jobs and resolve the WTTJ URL from the SendGrid redirect without a
        # session; it just won't be able to click Apply and get the ATS URL.
        login_wait = 0 if args.headless else DEFAULT_LOGIN_WAIT_TIMEOUT_S
        resolver_cm = WTTJBrowserResolver(
            user_data_dir=args.wttj_user_data_dir,
            headless=args.headless,
            pause_ms=args.pause_ms,
            debug_dir=args.debug_dir,
            login_wait_s=login_wait,
        )
        resolver = resolver_cm.__enter__()
    else:
        print(
            warn(
                "  ⚠  Browser resolver OFF — records may keep only the WTTJ job URL unless cached."
            ),
            flush=True,
        )

    try:
        total_emails = len(email_records)
        for email_idx, meta in enumerate(email_records, 1):
            matches, match_stats = extract_wttj_job_matches_from_email(
                meta,
                skip_internships=not args.include_wttj_internships,
            )
            stats["job_links_found"] += match_stats.get("job_links_found", 0)
            stats["job_matches_kept"] += match_stats.get("matches_kept", 0)
            stats["job_matches_skipped_internship"] += match_stats.get(
                "matches_skipped_internship", 0
            )

            if not matches:
                print(
                    dim(
                        f"  [{email_idx}/{total_emails}] No matches: {meta.get('subject', '')}"
                    ),
                    flush=True,
                )
                continue

            for match_idx, match in enumerate(matches, 1):
                company = match.get("company", "")
                title = match.get("title", "")
                wttj_job_url = match.get("wttj_job_url", "")
                # Use helper so we get both the ATS URL and the resolved WTTJ URL
                # from the cache — the old format stored only the ATS URL as a string.
                resolved_url, cached_wttj_url = (
                    _cache_get(cache, wttj_job_url) if wttj_job_url else ("", "")
                )
                resolve_result = None
                # Seed record_wttj_job_url from cache so that even on a cache hit
                # (resolver not called) wttj_dashboard_url gets the permanent WTTJ
                # URL instead of the ephemeral SendGrid tracking URL.
                record_wttj_job_url = cached_wttj_url or wttj_job_url
                if args.wttj_browser and wttj_job_url and not resolved_url and resolver:
                    prefix = (
                        f"{email_idx:03d}_{match_idx:02d}_{company}_{title}".lower()
                    )
                    prefix = "".join(ch if ch.isalnum() else "_" for ch in prefix)[:120]
                    resolve_result = resolver.resolve(
                        wttj_job_url, company=company, title=title, debug_prefix=prefix
                    )
                    resolved_url = resolve_result.selected_url or ""
                    # Prefer the clean resolved WTTJ URL (no tracking params).
                    # Falls back to page_url_before_click for backward compat.
                    if resolve_result.resolved_wttj_url:
                        record_wttj_job_url = resolve_result.resolved_wttj_url
                    elif resolve_result and is_wttj_job_detail_url(
                        resolve_result.page_url_before_click
                    ):
                        record_wttj_job_url = (
                            resolve_result.page_url_before_click.split("?")[0]
                        )
                    # Cache both URLs for available jobs so future runs can use the
                    # permanent WTTJ URL for wttj_dashboard_url and availability checks.
                    if not resolve_result.job_unavailable:
                        new_wttj_url = (
                            record_wttj_job_url
                            if record_wttj_job_url != wttj_job_url
                            else ""
                        )
                        if resolved_url or new_wttj_url:
                            _cache_set(cache, wttj_job_url, resolved_url, new_wttj_url)
                            write_json(args.wttj_cache, cache, pretty=True)

                # Skip dead listings — no record is written for unavailable jobs.
                if resolve_result and resolve_result.job_unavailable:
                    print(
                        err(
                            f"  [{email_idx}/{total_emails}.{match_idx}/{len(matches)}]"
                        )
                        + dim(f" ✗ unavailable: {company} — {title}"),
                        flush=True,
                    )
                    continue

                record = wttj_email_to_master_record(
                    meta,
                    resolved_job_url=resolved_url,
                    wttj_job_url=record_wttj_job_url,
                    company=company,
                    title=title,
                    match_context=match.get("context", ""),
                    email_text=match.get("email_text", ""),
                )
                if isinstance(record.get("raw_listing"), dict):
                    record["raw_listing"]["email_link_candidates"] = match.get(
                        "email_link_candidates", []
                    )
                    record["raw_listing"]["email_navigation_url"] = wttj_job_url
                    record["raw_listing"]["email_match_index"] = match_idx
                    record["raw_listing"]["email_match_count"] = len(matches)
                    if resolve_result:
                        record["raw_listing"]["browser_resolve_result"] = {
                            "selected_url": resolve_result.selected_url,
                            "clicked_selector": resolve_result.clicked_selector,
                            "modal_detected": resolve_result.modal_detected,
                            "error": resolve_result.error,
                            "job_unavailable": resolve_result.job_unavailable,
                            "resolved_wttj_url": resolve_result.resolved_wttj_url,
                        }

                is_new = dedupe.add(record)
                if is_new:
                    records.append(record)
                    stream(args.master_jsonl, record)
                    stats["records_written"] += 1
                status = ok("✓ new") if is_new else dim("~ dup")
                print(
                    f"  {dim(f'[{email_idx}/{total_emails}.{match_idx}/{len(matches)}]')}"
                    f" {status}  {bright_white(company)} — {dim(title)}",
                    flush=True,
                )
    finally:
        if resolver_cm:
            resolver_cm.__exit__(None, None, None)
        write_json(args.wttj_cache, cache, pretty=True)
        wrote = stats["records_written"]
        skipped = stats.get("job_matches_skipped_internship", 0)
        print(
            ok("  ✓ WTTJ done")
            + dim(f" — {wrote} new records written, {skipped} internships skipped"),
            flush=True,
        )


def main() -> None:
    load_dotenv_light()
    args = parse_args()

    jsonl_path = Path(args.master_jsonl)
    json_path = Path(args.master_json)
    error_path = Path(args.error_jsonl)

    # Clear the error log but do NOT delete the master outputs yet.
    # We write to temp files and atomically rename at the end so a crash
    # mid-run never leaves the master files empty or corrupt.
    if error_path.exists():
        error_path.unlink()

    dedupe = DedupeIndex()
    records: list[dict[str, Any]] = []

    # When both collection stages are skipped, load existing records from disk
    # so that --no-simplify --no-gmail --enrich-only re-enriches what's already there
    # rather than overwriting with an empty list.
    if args.no_simplify and args.no_gmail:
        existing = load_jsonl(jsonl_path)
        if existing:
            print(
                dim(
                    f"Collection skipped — loaded {len(existing):,} existing records for enrichment."
                ),
                flush=True,
            )
            records = existing
            for r in existing:
                dedupe.add(r)

    if not args.no_simplify:
        process_simplify(args, dedupe, records)
    if not args.no_gmail:
        process_wttj(args, dedupe, records)
    if not args.no_enrich:
        try:
            # Build a config that overrides the failed-stream path from the CLI
            # flag so the caller can redirect failures without touching env vars.
            enrich_cfg = EnrichConfig(failed_stream_path=args.failed_jsonl)
            records = enrich_records(records, cfg=enrich_cfg, limit=args.enrich_limit)
        except Exception as enrich_exc:
            # Enrichment failure must never discard already-collected records.
            # Log and continue so the pipeline still writes what it gathered.
            print(
                warn(
                    f"\n⚠  Enrichment pipeline raised an error and was skipped: {enrich_exc}"
                ),
                flush=True,
            )

    final = sort_records_newest_first([coerce_master_record(r) for r in records])

    # Write to sibling temp files, then atomically rename so the master
    # files are never left empty if the process is interrupted mid-write.
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_jsonl = jsonl_path.with_suffix(".jsonl.tmp")
    tmp_json = json_path.with_suffix(".json.tmp")

    with tmp_jsonl.open("w", encoding="utf-8") as f:
        for record in final:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_json(tmp_json, final, pretty=True)

    tmp_jsonl.replace(jsonl_path)
    tmp_json.replace(json_path)

    print(
        ok("✓ Done.")
        + f" Wrote {bright_white(str(len(final)))} records"
        + dim(f" → {jsonl_path}"),
        flush=True,
    )


if __name__ == "__main__":
    main()

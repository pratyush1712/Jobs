"""SimplifyJobs GitHub ingestion."""

from __future__ import annotations

from typing import Any

import requests

from .constants import (
    ADVANCED_DEGREE_KEYWORDS,
    BLOCKED_COMPANIES,
    CITIZENSHIP_KEYWORDS,
    DEFAULT_RAW_SIMPLIFY,
    KEEP_CATEGORY_KEYWORDS,
    SIMPLIFY_GITHUB_URL,
    SIMPLIFY_LISTINGS_URL,
)
from .models import coerce_master_record, empty_master_record
from .utils import clean_space, make_dedupe_key, parse_unix_epoch_to_iso, write_json


def fetch_simplify_listings(raw_output_path: str) -> list[dict[str, Any]]:
    resp = requests.get(SIMPLIFY_LISTINGS_URL, timeout=45)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise ValueError("Simplify listings JSON was not a list")
    write_json(raw_output_path, data, pretty=True)
    return data


def _contains_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(n.lower() in lower for n in needles)


def simplify_listing_passes_filters(listing: dict[str, Any]) -> tuple[bool, str]:
    if not listing.get("active", True):
        return False, "inactive"
    if not listing.get("is_visible", True):
        return False, "not_visible"
    sponsorship = clean_space(listing.get("sponsorship"))
    if sponsorship in {"U.S. Citizenship is Required", "Does Not Offer Sponsorship"}:
        return False, "blocked_sponsorship_or_citizenship"
    company_lower = (clean_space(listing.get("company_name")) or "").lower()
    if any(blocked.lower() in company_lower for blocked in BLOCKED_COMPANIES):
        return False, "blocked_company"
    degree_text = " ".join(clean_space(x) for x in listing.get("degrees", []) or [])
    if _contains_any(degree_text, ADVANCED_DEGREE_KEYWORDS):
        return False, "advanced_degree_required"
    scan = " ".join(
        clean_space(listing.get(k))
        for k in ("title", "category", "description", "requirements")
    )
    if _contains_any(scan, CITIZENSHIP_KEYWORDS):
        return False, "citizenship_keyword"
    if not _contains_any(
        f"{listing.get('category', '')} {listing.get('title', '')}",
        KEEP_CATEGORY_KEYWORDS,
    ):
        return False, "category_not_relevant"
    return True, "ok"


def simplify_to_master_record(listing: dict[str, Any]) -> dict[str, Any]:
    locations = [clean_space(x) for x in listing.get("locations", []) if clean_space(x)]
    company = clean_space(listing.get("company_name"))
    title = clean_space(listing.get("title"))
    job_url = clean_space(listing.get("url"))
    record = empty_master_record()
    record.update(
        {
            "source": "simplify_github",
            "id": clean_space(listing.get("id")),
            "company": company,
            "company_url": clean_space(listing.get("company_url")),
            "job_title": title,
            "locations": locations,
            "location": ", ".join(locations),
            "seniority": "new_grad",
            "remote_policy": "remote"
            if "remote" in " ".join(locations).lower()
            else "",
            "job_url": job_url,
            "visa_sponsorship_policy": clean_space(listing.get("sponsorship")),
            "keywords": [clean_space(listing.get("category"))]
            if listing.get("category")
            else [],
            "confidence": "medium",
            "active": bool(listing.get("active", True)),
            "date_posted_raw": str(listing.get("date_posted", "")),
            "date_posted_human": parse_unix_epoch_to_iso(listing.get("date_posted")),
            "simplify_url": SIMPLIFY_GITHUB_URL,
            "raw_listing": listing,
        }
    )
    record["dedupe_key"] = make_dedupe_key(job_url, company, title, locations)
    return coerce_master_record(record)


def build_simplify_records(
    raw_output_path: str = DEFAULT_RAW_SIMPLIFY,
) -> list[dict[str, Any]]:
    out = []
    for listing in fetch_simplify_listings(raw_output_path):
        ok, _reason = simplify_listing_passes_filters(listing)
        if ok:
            out.append(simplify_to_master_record(listing))
    return out

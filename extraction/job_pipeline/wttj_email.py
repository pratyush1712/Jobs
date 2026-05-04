"""Welcome to the Jungle Gmail parsing.

This module extracts one or more job matches from a single WTTJ email.
Internship filtering happens at the *job match* level before URL resolution,
Playwright modal resolution, or OpenAI enrichment.

Important correction:
WTTJ emails use SendGrid click-tracking links for both real job-card links and
footer/notification controls. Do NOT globally reject SendGrid. Also do NOT reject
a job-card link just because a large ancestor block contains footer text like
"Receive these notifications" or "Unsubscribe". Reject controls by URL and link
text; accept SendGrid only when its nearby context looks like a job card.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .constants import DEFAULT_GMAIL_TOKEN_FILE, DEFAULT_WTTJ_EMAIL_DEBUG_DIR, GMAIL_QUERY
from .filters import is_internship_text
from .gmail_client import get_gmail_service, list_all_message_ids, read_message
from .models import coerce_master_record, empty_master_record
from .utils import (
    clean_space,
    clean_text,
    html_to_text,
    is_sendgrid_tracking_url,
    is_wttj_email_control_url,
    is_wttj_job_detail_url,
    make_dedupe_key,
    normalize_url_for_dedupe,
    unwrap_possible_redirect_url,
)

ROLE_HINTS = [
    "software",
    "engineer",
    "developer",
    "data",
    "machine learning",
    "ml",
    "ai",
    "product",
    "designer",
    "analyst",
    "scientist",
    "backend",
    "frontend",
    "full stack",
    "full-stack",
    "devops",
    "infrastructure",
    "security",
    "platform",
    "mobile",
    "ios",
    "android",
    "technical staff",
    "staff",
    "resident",
    "builder",
    "build",
    "apprentice",
]

JOB_CARD_HINTS = [
    "salary",
    "compensation",
    "remote",
    "hybrid",
    "san francisco",
    "new york",
    "bay area",
    "engineer",
    "developer",
    "scientist",
    "analyst",
    "product",
    "technical staff",
    "staff",
    "resident",
]

CONTROL_TEXTS_EXACT = {
    "never",
    "weekly",
    "daily",
    "change email frequency",
    "manage email notifications",
    "unsubscribe",
    "email preferences",
    "notification settings",
    "privacy policy",
    "terms of use",
    "terms",
    "privacy",
}

CONTROL_TEXT_HINTS = [
    "unsubscribe",
    "manage email",
    "email frequency",
    "notification settings",
    "privacy policy",
    "terms of use",
    "settings/manage/candidate",
    "settings/unsubscribe",
]

GENERIC_MATCH_TEXTS = {
    "see all top matches",
    "view all matches",
    "all top matches",
    "see matches",
    "view matches",
}

NOISE_LINES = {
    "new job notification",
    "a new job matches your search preferences",
    "see all top matches",
    "receive these notifications:",
    "never",
    "weekly",
    "daily",
    "change email frequency",
    "manage email notifications",
    "unsubscribe",
    "welcome to the jungle is a trading name of otta technology ltd.",
}

_LOCATION_PATTERNS = [
    "san francisco", "bay area", "new york", "seattle", "los angeles",
    "chicago", "boston", "austin", "denver", "portland", "washington",
    "atlanta", "miami", "remote", "hybrid", "within the", "united states",
    "united kingdom", "canada", "+ 1 more", "+ 2 more",
]


def parse_new_match_subject(subject: str) -> tuple[str, str]:
    match = re.search(r"New match:\s*(.*?)\s+at\s+(.+)$", subject or "", flags=re.I)
    if not match:
        return "", ""
    return clean_space(match.group(2)), clean_space(match.group(1))


def email_body_text(email_meta: dict[str, Any]) -> str:
    bodies = email_meta.get("bodies", {}) or {}
    raw_html = "\n".join(bodies.get("text/html", []) or [])
    raw_plain = "\n".join(bodies.get("text/plain", []) or [])
    return clean_text(raw_plain or html_to_text(raw_html))


def _ancestor_context(a: Any) -> str:
    """Capture enough nearby card text to infer company/title for multi-job emails."""
    chunks: list[str] = []
    current = a
    for _ in range(6):
        current = getattr(current, "parent", None)
        if current is None:
            break
        text = clean_space(current.get_text("\n", strip=True))
        if text and text not in chunks:
            chunks.append(text)
    return "\n---\n".join(chunks)[:2500]


def is_control_link_text(text: str) -> bool:
    """Reject footer/notification controls by link text only.

    Do not inspect broad ancestor context here. Valid WTTJ job-card links can have
    a huge ancestor block that also contains the email footer.
    """
    lowered = clean_space(text).lower().strip(" .|-:")
    if not lowered:
        return False
    if lowered in CONTROL_TEXTS_EXACT:
        return True
    return any(hint in lowered for hint in CONTROL_TEXT_HINTS)


def is_generic_matches_link_text(text: str) -> bool:
    lowered = clean_space(text).lower().strip(" .|-:")
    return lowered in GENERIC_MATCH_TEXTS


def is_job_card_context(text: str, context: str, fallback_company: str = "", fallback_title: str = "") -> bool:
    """Return True if a link appears attached to a real job card.

    SendGrid links are accepted only after this check. Generic dashboard links and
    notification controls are rejected, while empty-image/card links with strong
    company/title/role context are accepted.
    """
    if is_control_link_text(text):
        return False
    if is_generic_matches_link_text(text):
        return False

    combined = f"{text}\n{context}".lower()
    role_signal = any(hint in combined for hint in ROLE_HINTS)
    job_card_signal = any(hint in combined for hint in JOB_CARD_HINTS)
    company_signal = bool(fallback_company and fallback_company.lower() in combined)
    title_signal = bool(fallback_title and fallback_title.lower() in combined)

    # Single-job WTTJ emails often have a blank/image link wrapping a card. The
    # subject company/title is the safest signal there.
    if company_signal and title_signal:
        return True
    if title_signal and job_card_signal:
        return True
    if company_signal and role_signal and job_card_signal:
        return True
    return role_signal and job_card_signal


def extract_links_from_html(raw_html: str, fallback_company: str = "", fallback_title: str = "") -> list[dict[str, str]]:
    """Extract actionable WTTJ job-navigation links from email HTML.

    This keeps SendGrid click URLs only when they belong to a job-card context.
    It rejects footer controls before Playwright ever sees them.
    """
    soup = BeautifulSoup(raw_html or "", "html.parser")
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        raw_href = clean_space(a.get("href"))
        if not raw_href:
            continue

        absolute_raw_href = urljoin("https://app.welcometothejungle.com", raw_href)
        text = clean_space(a.get_text(" ", strip=True))
        context = _ancestor_context(a) or text

        if is_control_link_text(text) or is_wttj_email_control_url(absolute_raw_href):
            continue
        if is_generic_matches_link_text(text):
            continue

        candidate_href = unwrap_possible_redirect_url(absolute_raw_href)

        if is_sendgrid_tracking_url(candidate_href):
            if not is_job_card_context(text, context, fallback_company, fallback_title):
                continue
            navigation_href = candidate_href
        elif is_wttj_job_detail_url(candidate_href):
            navigation_href = candidate_href
        else:
            continue

        key = normalize_url_for_dedupe(navigation_href) or navigation_href
        if key in seen:
            continue
        seen.add(key)

        links.append(
            {
                "href": navigation_href,
                "raw_href": absolute_raw_href,
                "text": text,
                "context": context,
                "is_sendgrid_tracking": str(is_sendgrid_tracking_url(navigation_href)).lower(),
            }
        )
    return links


def _bad_url(url: str) -> bool:
    if is_wttj_email_control_url(url):
        return True
    return not (is_wttj_job_detail_url(url) or is_sendgrid_tracking_url(url))


def score_wttj_email_link(link: dict[str, str], company: str = "", title: str = "") -> int:
    href = (link.get("href") or "").lower()
    text = (link.get("text") or "").lower()
    context = (link.get("context") or "").lower()
    if not href or _bad_url(href):
        return -999
    if is_control_link_text(text) or is_generic_matches_link_text(text):
        return -999

    score = 0
    if is_wttj_job_detail_url(href):
        score += 160
    elif is_sendgrid_tracking_url(href):
        score += 130

    if company and company.lower() in context:
        score += 15
    if title and title.lower() in context:
        score += 15
    if any(word in text for word in ["see job", "view job", "apply", "see offer", "open role"]):
        score += 10
    if is_wttj_email_control_url(href):
        score -= 500
    return score


def pick_wttj_job_detail_url(raw_html: str, company: str, title: str) -> tuple[str, list[dict[str, Any]]]:
    """Backward-compatible helper: returns only the best job URL."""
    candidates: list[dict[str, Any]] = []
    for link in extract_links_from_html(raw_html, company, title):
        item: dict[str, Any] = dict(link)
        item["score"] = score_wttj_email_link(link, company, title)
        candidates.append(item)
    candidates.sort(key=lambda x: x.get("score", -999), reverse=True)
    for item in candidates:
        if item.get("score", -999) > 0:
            return str(item.get("href") or ""), candidates
    return "", candidates


def _clean_context_lines(context: str) -> list[str]:
    raw_lines: list[str] = []
    for part in re.split(r"[\n|]+", context or ""):
        line = clean_space(part)
        if not line:
            continue
        lowered = line.lower().strip(" .|-")
        if lowered in NOISE_LINES:
            continue
        if is_control_link_text(line) or is_generic_matches_link_text(line):
            continue
        if len(line) > 180:
            continue
        if line not in raw_lines:
            raw_lines.append(line)
    return raw_lines


def _is_salary_line(text: str) -> bool:
    return clean_space(text).lower().startswith("salary:")


def _is_level_line(text: str) -> bool:
    stripped = clean_space(text)
    return len(stripped) >= 3 and stripped.startswith("(") and stripped.endswith(")")


def _looks_like_location(text: str) -> bool:
    """Return True if the line looks like a standalone location entry."""
    lowered = clean_space(text).lower().strip()
    if len(lowered) > 90 or not lowered:
        return False
    if _is_salary_line(lowered) or _is_level_line(lowered):
        return False
    return any(pat in lowered for pat in _LOCATION_PATTERNS)


def _is_email_boilerplate_line(text: str) -> bool:
    lowered = clean_space(text).lower().strip(" .|-")
    if not lowered:
        return True
    if lowered in NOISE_LINES:
        return True
    if lowered.startswith("a new job matches your search preferences"):
        return True
    if lowered.startswith("there are new jobs matching your search preferences"):
        return True
    if lowered.startswith("receive these notifications"):
        return True
    if lowered.startswith("welcome to the jungle is a trading name"):
        return True
    if lowered.startswith("first floor, mindspace"):
        return True
    return is_control_link_text(text) or is_generic_matches_link_text(text)


def _email_job_section_lines(email_text: str) -> list[str]:
    """Return only the visible job-card lines from a WTTJ plaintext email."""
    out: list[str] = []
    in_jobs = False
    for raw_line in (email_text or "").split("\n"):
        line = clean_space(raw_line)
        if not line:
            continue

        lowered = line.lower().strip(" .|-")
        if lowered == "new job notification":
            in_jobs = False
            continue
        if lowered.startswith("a new job matches your search preferences") or lowered.startswith("there are new jobs matching your search preferences"):
            in_jobs = True
            continue
        if not in_jobs:
            continue
        if lowered in GENERIC_MATCH_TEXTS or lowered.startswith("see all top matches"):
            break
        if lowered.startswith("receive these notifications"):
            break
        if _is_email_boilerplate_line(line):
            continue
        out.append(line)
    return out


def _parse_email_job_blocks(email_text: str) -> list[dict[str, str]]:
    """Parse WTTJ email plaintext into structured job blocks.

    WTTJ job cards are emitted sequentially as::

        CompanyName
        CompanyDescription
        JobTitle
        (Level)             <- optional
        Salary: $XXX-XXXK   <- optional
        Location

    The old parser used only ``Salary:`` as an anchor, which missed no-salary
    jobs and let footer/address lines become fake jobs. This parser first cuts
    the body down to the job-card section, then walks each card in order.
    """
    lines = _email_job_section_lines(email_text)
    blocks: list[dict[str, str]] = []
    i = 0

    while i + 2 < len(lines):
        company = lines[i]
        description = lines[i + 1]
        title = lines[i + 2]
        i += 3

        if _is_email_boilerplate_line(company) or _is_email_boilerplate_line(description) or _is_email_boilerplate_line(title):
            continue
        if _is_salary_line(company) or _is_salary_line(description) or _is_salary_line(title):
            continue
        if _looks_like_location(company) or _looks_like_location(description):
            continue

        if i < len(lines) and _is_level_line(lines[i]):
            title = f"{title} {lines[i]}"
            i += 1

        if i < len(lines) and _is_salary_line(lines[i]):
            i += 1

        if i < len(lines) and _looks_like_location(lines[i]):
            i += 1

        blocks.append({"company": clean_space(company), "description": clean_space(description), "title": clean_space(title)})

    return blocks


def _compact_match_text(text: str) -> str:
    return re.sub(r"\s+", " ", clean_space(text).lower())


def _title_without_level(title: str) -> str:
    return clean_space(re.sub(r"\s*\([^)]*\)\s*$", "", title))


def _match_card_to_block(
    link_text: str,
    context: str,
    blocks: list[dict[str, str]],
) -> dict[str, str] | None:
    """Match a link candidate's narrow card text to a parsed job block."""
    narrow = (context or "").split("---", 1)[0]
    haystack = _compact_match_text(f"{link_text} {narrow}")

    best: dict[str, str] | None = None
    best_score = 0
    for block in blocks:
        company = clean_space(block.get("company", ""))
        title = clean_space(block.get("title", ""))
        description = clean_space(block.get("description", ""))
        if not company or not title:
            continue

        company_l = _compact_match_text(company)
        title_l = _compact_match_text(title)
        base_title_l = _compact_match_text(_title_without_level(title))
        description_l = _compact_match_text(description)

        company_hit = company_l in haystack
        title_hit = title_l in haystack
        base_title_hit = bool(base_title_l and base_title_l in haystack)
        description_hit = bool(description_l and description_l in haystack)

        score = 0
        if company_hit:
            score += 100
        if title_hit:
            score += 45
        elif base_title_hit:
            score += 25
        if description_hit:
            score += 30
        if haystack.startswith(company_l):
            score += 20

        if score > best_score:
            best_score = score
            best = block

    return best if best is not None and best_score >= 100 else None


def infer_company_title_from_context(context: str, fallback_company: str = "", fallback_title: str = "") -> tuple[str, str]:
    """Best-effort extraction from a WTTJ email job card.

    This intentionally only inspects the first/narrow ancestor section. Wider
    ancestors often contain every job card plus the footer, which caused titles
    and companies from different cards to be mixed together.
    """
    narrow = (context or "").split("---", 1)[0].strip()
    narrow_l = _compact_match_text(narrow)

    company = fallback_company if fallback_company and _compact_match_text(fallback_company) in narrow_l else ""
    title = fallback_title if fallback_title and _compact_match_text(fallback_title) in narrow_l else ""
    if company and title:
        return clean_space(company), clean_space(title)

    lines = _clean_context_lines(narrow)
    if len(lines) >= 3:
        parsed_title = lines[2]
        if len(lines) >= 4 and _is_level_line(lines[3]):
            parsed_title = f"{parsed_title} {lines[3]}"
        parsed_company = lines[0]
        if not _looks_like_location(parsed_company) and not _is_salary_line(parsed_company):
            return clean_space(company or parsed_company), clean_space(title or parsed_title)

    if not title:
        for line in lines:
            lowered = line.lower()
            if any(hint in lowered for hint in ROLE_HINTS) and not _is_salary_line(line) and not _looks_like_location(line):
                title = re.split(r"\s+Salary:\s+|\s+Location:\s+", line, maxsplit=1, flags=re.I)[0]
                break

    if not company and lines:
        first = lines[0]
        if not _looks_like_location(first) and not _is_salary_line(first):
            company = first

    return clean_space(company or fallback_company), clean_space(title or fallback_title)


def _write_debug_candidates(email_meta: dict[str, Any], candidates: list[dict[str, Any]], debug_dir: str = DEFAULT_WTTJ_EMAIL_DEBUG_DIR) -> None:
    """Write candidate diagnostics when an email produces zero job matches."""
    try:
        Path(debug_dir).mkdir(parents=True, exist_ok=True)
        raw_id = str(email_meta.get("gmail_internal_id") or email_meta.get("thread_id") or "email")
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", raw_id)[:100]
        path = Path(debug_dir) / f"{safe_id}_link_candidates.json"
        payload = {
            "subject": email_meta.get("subject", ""),
            "gmail_internal_id": email_meta.get("gmail_internal_id", ""),
            "thread_id": email_meta.get("thread_id", ""),
            "candidate_count": len(candidates),
            "candidates": candidates[:50],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def extract_wttj_job_matches_from_email(
    email_meta: dict[str, Any],
    skip_internships: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Extract all WTTJ job matches from one email.

    Returns (matches, stats). Each match contains company, title, wttj_job_url,
    context, and email_link_candidates. Internship matches are skipped here so
    the caller does not parse links, open pages, or enrich them.
    """
    subject_company, subject_title = parse_new_match_subject(email_meta.get("subject", ""))
    bodies = email_meta.get("bodies", {}) or {}
    raw_html = "\n".join(bodies.get("text/html", []) or [])
    email_text = email_body_text(email_meta)

    candidates: list[dict[str, Any]] = []
    for link in extract_links_from_html(raw_html, subject_company, subject_title):
        item: dict[str, Any] = dict(link)
        item["score"] = score_wttj_email_link(link, subject_company, subject_title)
        candidates.append(item)
    candidates.sort(key=lambda x: x.get("score", -999), reverse=True)

    job_blocks = _parse_email_job_blocks(email_text)

    matches: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    stats = {"job_links_found": 0, "matches_kept": 0, "matches_skipped_internship": 0}

    for item in candidates:
        score = int(item.get("score", -999))
        href = str(item.get("href") or "")
        href_key = normalize_url_for_dedupe(href) or href
        if score <= 0 or not href or href_key in seen_urls:
            continue
        seen_urls.add(href_key)
        stats["job_links_found"] += 1

        context = str(item.get("context") or "")
        link_text = str(item.get("text") or "")

        block = _match_card_to_block(link_text, context, job_blocks)
        if block:
            company = block["company"]
            title = block["title"]
        else:
            company, title = infer_company_title_from_context(context, subject_company, subject_title)

        internship_scan_text = "\n".join([title, company, context, link_text])
        if skip_internships and is_internship_text(internship_scan_text):
            stats["matches_skipped_internship"] += 1
            print(f"Skipping WTTJ internship match: {company} - {title}")
            continue

        matches.append(
            {
                "company": company,
                "title": title,
                "wttj_job_url": href,
                "context": context,
                "link_text": link_text,
                "email_link_candidates": candidates[:10],
                "email_text": email_text,
            }
        )
        stats["matches_kept"] += 1

    if not matches:
        _write_debug_candidates(email_meta, candidates)
    return matches, stats


def wttj_email_to_master_record(
    email_meta: dict[str, Any],
    resolved_job_url: str = "",
    wttj_job_url: str = "",
    company: str = "",
    title: str = "",
    match_context: str = "",
    email_text: str = "",
) -> dict[str, Any]:
    fallback_company, fallback_title = parse_new_match_subject(email_meta.get("subject", ""))
    company = clean_space(company or fallback_company)
    title = clean_space(title or fallback_title)
    email_text = clean_text(email_text or email_body_text(email_meta))

    record = empty_master_record()
    record.update(
        {
            "source": "wttj_gmail",
            "id": email_meta.get("gmail_internal_id", ""),
            "company": company,
            "job_title": title,
            "seniority": "new_grad",
            "job_url": resolved_job_url,
            "wttj_dashboard_url": wttj_job_url,
            "confidence": "medium" if resolved_job_url else "low",
            "date_posted_raw": email_meta.get("email_date", ""),
            "date_posted_human": email_meta.get("email_date", ""),
            "gmail_link": email_meta.get("gmail_link", ""),
            "message_id_header": email_meta.get("message_id_header", ""),
            "thread_id": email_meta.get("thread_id", ""),
            "email_date": email_meta.get("email_date", ""),
            "email_subject": email_meta.get("subject", ""),
            "raw_listing": {
                **{k: v for k, v in email_meta.items() if k != "bodies"},
                "wttj_job_url": wttj_job_url,
                "resolved_job_url": resolved_job_url,
                "match_context": match_context,
                "email_text": email_text,
            },
        }
    )
    record["dedupe_key"] = make_dedupe_key(resolved_job_url or wttj_job_url, company, title, [])
    return coerce_master_record(record)


def fetch_wttj_email_records(
    credentials_file: str | None = None,
    token_file: str = DEFAULT_GMAIL_TOKEN_FILE,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Fetch WTTJ Gmail messages.

    Internship filtering is intentionally not applied at whole-email level because
    one email can contain multiple job cards. Filtering happens per extracted job
    match in extract_wttj_job_matches_from_email().
    """
    service = get_gmail_service(credentials_file=credentials_file, token_file=token_file)
    message_ids = list_all_message_ids(service, GMAIL_QUERY, limit=limit)
    records: list[dict[str, Any]] = []
    stats = {"emails_fetched": 0}
    for gmail_id in message_ids:
        meta = read_message(service, gmail_id)
        stats["emails_fetched"] += 1
        records.append(meta)
    return records, stats

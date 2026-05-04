"""Eligibility filters shared by extraction steps."""
from __future__ import annotations

import re
from typing import Any

from .constants import INTERNSHIP_KEYWORD_PATTERNS
from .utils import clean_space, html_to_text

INTERNSHIP_RE = re.compile("|".join(f"(?:{p})" for p in INTERNSHIP_KEYWORD_PATTERNS), flags=re.I)


def is_internship_text(text: str) -> bool:
    """Return True for internship/co-op/apprenticeship-style wording.

    Uses word-boundary regexes so unrelated words like "internal" and
    "international" do not match `intern`.
    """
    return bool(INTERNSHIP_RE.search(text or ""))


def wttj_email_internship_reason(email_meta: dict[str, Any]) -> str:
    """Return a skip reason if the WTTJ email appears to be for an internship.

    This is intentionally designed to run before URL parsing, Playwright Apply
    modal resolution, or OpenAI enrichment.
    """
    subject = clean_space(email_meta.get("subject"))
    snippet = clean_space(email_meta.get("snippet"))
    bodies = email_meta.get("bodies", {}) or {}
    plain = "\n".join(bodies.get("text/plain", []) or [])
    html = "\n".join(bodies.get("text/html", []) or [])
    email_text = clean_space(plain or html_to_text(html))

    # Subject/title is the strongest signal and should be checked first.
    if is_internship_text(subject):
        return "internship_in_subject"
    if is_internship_text(snippet):
        return "internship_in_snippet"
    if is_internship_text(email_text[:5000]):
        return "internship_in_email_body"
    return ""

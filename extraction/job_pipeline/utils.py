"""General utilities."""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse, urlunparse

from bs4 import BeautifulSoup


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def clean_text(value: Any) -> str:
    text = re.sub(r"\r", "\n", str(value or ""))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return clean_text(soup.get_text("\n", strip=True))


def decode_base64url(data: str | None) -> str:
    if not data:
        return ""
    data += "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def read_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, obj: Any, pretty: bool = True) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2 if pretty else None)
        f.write("\n")


def append_jsonl(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            pass
    return rows


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [clean_space(x) for x in value if clean_space(x)]
    if isinstance(value, str) and value.strip():
        return [clean_space(value)]
    return []


def parse_unix_epoch_to_iso(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return str(value or "")


def parse_date_loose(value: Any) -> datetime:
    if value in (None, ""):
        return datetime.fromtimestamp(0, timezone.utc)
    try:
        text = str(value)
        if text.isdigit():
            return datetime.fromtimestamp(float(text), timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return datetime.fromtimestamp(0, timezone.utc)


def sort_records_newest_first(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda r: parse_date_loose(r.get("date_posted_human")), reverse=True)


def normalize_url_for_dedupe(url: str | None) -> str:
    """Normalize a URL for deduplication, preserving path case.

    Hostnames are case-insensitive (lowercased), but path segments
    preserve their original casing because some hosts (e.g. WTTJ job
    slugs like ``9asUS1Lb``) use case-sensitive identifiers.
    """
    raw = (url or "").encode("ascii", errors="ignore").decode("ascii").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+$", "", parsed.path or "")
    if not netloc:
        raw = re.sub(r"^https?://", "", raw, flags=re.I)
        raw = re.sub(r"^www\.", "", raw, flags=re.I)
        without_qs = raw.split("?", 1)[0].rstrip("/")
        slash_idx = without_qs.find("/")
        if slash_idx >= 0:
            return without_qs[:slash_idx].lower() + without_qs[slash_idx:]
        return without_qs.lower()
    return f"{netloc}{path}"


def composite_hash(company: str, title: str, first_location: str = "") -> str:
    def alnum(x: str) -> str:
        return re.sub(r"[^a-z0-9]", "", x.lower())
    payload = f"{alnum(company)}::{alnum(title)}::{alnum(first_location)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_dedupe_key(job_url: str, company: str, title: str, locations: list[str] | None = None) -> str:
    url_key = normalize_url_for_dedupe(job_url)
    if url_key:
        return url_key
    return composite_hash(company, title, (locations or [""])[0] if locations else "")


def build_gmail_link(message_id_header: str) -> str:
    msg_id = (message_id_header or "").strip().strip("<>").strip()
    return f"https://mail.google.com/mail/#search/{quote(f'rfc822msgid:{msg_id}', safe=':@')}" if msg_id else ""


def unwrap_possible_redirect_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for key in ("url", "u", "redirect", "redirect_url", "target", "target_url"):
            if params.get(key):
                candidate = unquote(params[key][0])
                if candidate.startswith(("http://", "https://")):
                    return candidate
    except Exception:
        pass
    return url


def url_host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""


def url_path(url: str) -> str:
    try:
        return urlparse(url).path or ""
    except Exception:
        return ""


def is_sendgrid_tracking_url(url: str) -> bool:
    host = url_host(url)
    path = url_path(url).lower()
    return "sendgrid.net" in host or path.startswith("/ls/click")


def is_wttj_email_control_url(url: str) -> bool:
    lower = (url or "").lower()
    host = url_host(url)
    return (
        "email.welcometothejungle.com" in host
        or "settings/manage/candidate" in lower
        or "settings/unsubscribe" in lower
        or "manage email" in lower
        or "unsubscribe" in lower
        or "preferences" in lower
    )


def is_wttj_job_detail_url(url: str) -> bool:
    lower = (url or "").lower()
    host = url_host(url)
    path = url_path(url).lower()
    if is_sendgrid_tracking_url(url) or is_wttj_email_control_url(url):
        return False
    if "welcometothejungle.com" not in host and "welcome-to-the-jungle.com" not in host:
        return False
    return "/jobs/" in path

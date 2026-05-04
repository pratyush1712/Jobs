from __future__ import annotations

from typing import Any

from .utils import make_dedupe_key, normalize_url_for_dedupe


class DedupeIndex:
    """Tracks seen jobs by URL and dedupe key.

    URLs are normalized before comparison. Hostnames are lowercased by
    ``normalize_url_for_dedupe`` while path casing is preserved so that
    case-sensitive job slugs (including WTTJ slugs) are not collapsed.
    """

    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.url_keys: set[str] = set()

    def add(self, record: dict[str, Any]) -> bool:
        url_key = normalize_url_for_dedupe(str(record.get("job_url") or ""))
        dedupe_key = str(record.get("dedupe_key") or "") or make_dedupe_key(
            str(record.get("job_url") or ""),
            str(record.get("company") or ""),
            str(record.get("job_title") or ""),
            record.get("locations") or [],
        )
        record["dedupe_key"] = dedupe_key
        url_check = url_key if url_key else ""
        dedupe_check = dedupe_key if dedupe_key else ""
        if url_check and url_check in self.url_keys:
            return False
        if dedupe_check and dedupe_check in self.keys:
            return False
        if url_check:
            self.url_keys.add(url_check)
        if dedupe_check:
            self.keys.add(dedupe_check)
        return True

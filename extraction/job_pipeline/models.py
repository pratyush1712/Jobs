"""Master output schema helpers."""
from __future__ import annotations
from typing import Any
from .utils import now_iso

MASTER_DEFAULTS: dict[str, Any] = {
    "source": "", "dedupe_key": "", "id": "", "company": "", "company_url": "",
    "job_title": "", "locations": [], "location": "", "employment_type": "", "seniority": "",
    "remote_policy": "", "job_url": "", "wttj_dashboard_url": "", "page_title": "",
    "compensation": "", "benefits": "", "relocation": "", "visa_sponsorship_policy": "",
    "summary": "", "tech_stack": [], "resume_keywords": [], "keywords": [],
    "required_skills": [], "preferred_skills": [],
    "responsibilities": [], "requirements": [], "nice_to_have": [], "confidence": "low",
    "application_status": "interested", "date_applied": "", "referral": "", "contact_name": "",
    "contact_email": "", "notes": "", "next_follow_up_date": "", "salary_expectation": "",
    "imported_at": "", "updated_at": "", "active": True, "date_posted_raw": "",
    "date_posted_human": "", "faang_plus": False, "simplify_url": "", "gmail_link": "",
    "message_id_header": "", "thread_id": "", "email_date": "", "email_subject": "",
    "raw_listing": {},
}
LIST_FIELDS = {"locations", "tech_stack", "resume_keywords", "keywords", "required_skills", "preferred_skills", "responsibilities", "requirements", "nice_to_have"}


def empty_master_record() -> dict[str, Any]:
    now = now_iso()
    record: dict[str, Any] = {}
    for key, value in MASTER_DEFAULTS.items():
        record[key] = list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value
    record["imported_at"] = now
    record["updated_at"] = now
    return record


def coerce_master_record(record: dict[str, Any]) -> dict[str, Any]:
    base = empty_master_record()
    base.update(record)
    for key in LIST_FIELDS:
        if base.get(key) is None:
            base[key] = []
        elif not isinstance(base.get(key), list):
            base[key] = [str(base[key])]
    if not base.get("location") and base.get("locations"):
        base["location"] = ", ".join(str(x) for x in base["locations"])
    if not isinstance(base.get("raw_listing"), dict):
        base["raw_listing"] = {"value": base.get("raw_listing")}
    return {key: base[key] for key in MASTER_DEFAULTS}


def merge_enrichment_fields(record: dict[str, Any], enrichment: dict[str, Any] | None) -> dict[str, Any]:
    if not enrichment:
        return coerce_master_record(record)
    out = dict(record)
    mapping = {"visa_sponsorship": "visa_sponsorship_policy", "visa_sponsorship_policy": "visa_sponsorship_policy"}
    for key, value in enrichment.items():
        target = mapping.get(key, key)
        if target in MASTER_DEFAULTS and value not in (None, "", []):
            if out.get(target) in (None, "", []):
                out[target] = value
    out["updated_at"] = now_iso()
    return coerce_master_record(out)

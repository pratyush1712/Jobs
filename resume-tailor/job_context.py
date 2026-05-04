def build_jd_block(job: dict) -> str:
    """Render a clean job description block from a job dict."""
    lines = [
        f"Company:         {job.get('company', '')}",
        f"Job Title:       {job.get('job_title', '')}",
        f"Location:        {job.get('location', '')}",
        f"Employment:      {job.get('employment_type', '')} | {job.get('remote_policy', '')}",
        f"Seniority:       {job.get('seniority', '')}",
        "",
        "Summary:",
        job.get("summary", ""),
        "",
        "Required Skills:",
        *[f"  - {s}" for s in job.get("required_skills", [])],
        "",
        "Preferred Skills:",
        *[f"  - {s}" for s in job.get("preferred_skills", [])],
        "",
        "Responsibilities:",
        *[f"  - {r}" for r in job.get("responsibilities", [])],
        "",
        "Keywords / Tech:",
        *[f"  - {k}" for k in job.get("keywords", [])],
        *[f"  - {k}" for k in job.get("resume_keywords", [])],
    ]
    return "\n".join(lines)

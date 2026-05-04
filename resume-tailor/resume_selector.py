from config import BASE_RESUME_FILE, RESUMES_DIR


def select_base_resume(job: dict) -> tuple[str, str]:
    """
    Always use main.tex as the base resume.
    Past company resumes (e.g. amazon.tex) are stored for reference only.

    Falls back to the most recently modified .tex if main.tex is missing.
    """
    # Config override
    if BASE_RESUME_FILE:
        fixed = RESUMES_DIR / BASE_RESUME_FILE
        if fixed.exists():
            return fixed.name, fixed.read_text(encoding="utf-8")

    # Primary: main.tex
    main = RESUMES_DIR / "main.tex"
    if main.exists():
        return "main.tex", main.read_text(encoding="utf-8")

    # Fallback: most recently modified (excludes company-named files heuristically)
    tex_files = sorted(
        RESUMES_DIR.glob("*.tex"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not tex_files:
        raise FileNotFoundError(f"No .tex files found in {RESUMES_DIR}")

    chosen = tex_files[0]
    return chosen.name, chosen.read_text(encoding="utf-8")


def get_past_resume(company: str) -> tuple[str, str] | None:
    """
    Optionally retrieve a past company resume by name for reference/diffing.
    Matches loosely: 'Amazon Web Services' → looks for amazon.tex
    """
    if not company:
        return None
    slug = company.lower().split()[
        0
    ]  # first word only: "Amazon Web Services" → "amazon"
    candidate = RESUMES_DIR / f"{slug}.tex"
    if candidate.exists():
        return candidate.name, candidate.read_text(encoding="utf-8")
    return None

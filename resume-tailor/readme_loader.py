from config import READMES_DIR

README_FILES = [
    "overview.md",
    "education.md",
    "skills.md",
    "projects.md",
    "affiliations.md",
    "experience.md",
]


def load_readmes() -> str:
    """Concatenate all readme files into one context block."""
    sections = []
    for fname in README_FILES:
        path = READMES_DIR / fname
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            sections.append(f"### {fname}\n{content}")
        else:
            sections.append(f"### {fname}\n[FILE NOT FOUND]")
    return "\n\n".join(sections)

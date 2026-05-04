"""Shared constants for the job extraction pipeline."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
EXTRACTION_DIR = PACKAGE_DIR.parent

def extraction_path(*parts: str) -> str:
    """Return an absolute path anchored to the extraction project directory."""
    return str(EXTRACTION_DIR.joinpath(*parts))

SIMPLIFY_LISTINGS_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
SIMPLIFY_GITHUB_URL = "https://github.com/SimplifyJobs/New-Grad-Positions"

GMAIL_QUERY = (
    'from:(help@welcometothejungle.com OR welcome@welcometothejungle.com '
    'OR help@welcome-to-the-jungle.com) subject:"New match:"'
)
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CITIZENSHIP_KEYWORDS = [
    "citizenship", "us citizen", "u.s. citizen", "usa citizen", "u.s. citizenship",
    "citizenship required", "require u.s. citizenship", "must be a u.s. citizen",
    "must be a us citizen", "us citizenship", "usa citizenship", "security clearance",
    "clearance required", "active clearance", "top secret", "secret clearance",
    "public trust", "eligible for security clearance",
]

# Defense contractors and companies whose roles universally require U.S. citizenship
# or a security clearance, regardless of what the Simplify sponsorship field says.
# Company names are matched case-insensitively as substrings of the listing's
# company_name field.
BLOCKED_COMPANIES: list[str] = [
    "anduril",
    "northrop grumman",
    "lockheed martin",
    "raytheon",
    "l3harris",
    "leidos",
    "saic",
    "booz allen",
    "general dynamics",
    "bae systems",
    "huntington ingalls",
    "hii",
    "mitre",
    "caci",
    "mantech",
    "peraton",
    "amentum",
    "rtx",
    "palantir",
]
ADVANCED_DEGREE_KEYWORDS = ["master", "phd", "ph.d", "mba", "doctorate", "advanced degree"]
KEEP_CATEGORY_KEYWORDS = ["software", "engineer", "data", "machine learning", "quant", "product"]

# WTTJ-specific early skip. These are intentionally applied before URL parsing,
# Playwright modal resolution, or OpenAI enrichment.
INTERNSHIP_KEYWORD_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\binternships\b",
    r"\bsummer\s+intern\b",
    r"\bsoftware\s+engineering\s+intern\b",
    r"\bswe\s+intern\b",
    r"\bdata\s+(science\s+)?intern\b",
    r"\bmachine\s+learning\s+intern\b",
    r"\bproduct\s+(manager\s+)?intern\b",
    r"\bco[-\s]?op\b",
    r"\bcoop\b",
    r"\bapprentice(ship)?\b",
    r"\btrainee\b",
    r"\bworking\s+student\b",
    r"\bstage\b",  # common internship wording in EU/French contexts
    r"\bstagiaire\b",
]

ATS_OR_JOB_HINTS = [
    "greenhouse.io", "job-boards.greenhouse.io", "boards.greenhouse.io", "lever.co",
    "jobs.lever.co", "ashbyhq.com", "jobs.ashbyhq.com", "workdayjobs.com",
    "myworkdayjobs.com", "smartrecruiters.com", "icims.com", "oraclecloud.com",
    "bamboohr.com", "recruitee.com", "rippling.com", "gusto.com", "personio.com",
    "pinpointhq.com", "workable.com", "applytojob.com", "jobs.", "careers.",
    "career.", "recruiting.",
]
BAD_URL_HINTS = [
    "unsubscribe", "preferences", "privacy", "terms", "cookie", "instagram", "facebook",
    "linkedin.com/company", "twitter.com", "x.com/", "/share", "cdn-cgi", "mailto:",
    "tel:", "javascript:", "#", "settings/manage/candidate", "email.welcometothejungle.com/settings", "sendgrid.net", "ct.sendgrid.net", "/ls/click",
]
APPLY_BUTTON_SELECTORS = [
    # Stable data-testid selector — most reliable when present (unauthenticated / direct-link view)
    "[data-testid='apply-button']",
    # Text-based fallbacks
    "button:has-text('Apply')", "a:has-text('Apply')", "[role='button']:has-text('Apply')",
    "[data-testid*='apply']:has-text('Apply')", "[data-testid*='Apply']:has-text('Apply')",
    "button:has-text('Postuler')", "a:has-text('Postuler')", "[role='button']:has-text('Postuler')",
]
MODAL_OR_DRAWER_SELECTORS = [
    "[role='dialog']", "[aria-modal='true']", "text=/Or apply on/i",
    "text=/apply on .* website/i", "text=/Apply with your profile/i",
    "[data-testid='apply-via-otta-button']",
]

DEFAULT_MASTER_JSONL = extraction_path("data", "jobs", "master_jobs.jsonl")
DEFAULT_MASTER_JSON = extraction_path("data", "jobs", "master_jobs.json")
DEFAULT_ERROR_JSONL = extraction_path("data", "jobs", "master_jobs_errors.jsonl")
DEFAULT_RAW_SIMPLIFY = extraction_path("data", "cache", "simplify_listings_raw.json")
DEFAULT_WTTJ_CACHE = extraction_path("data", "cache", "wttj_dashboard_links.json")
DEFAULT_WTTJ_DEBUG_DIR = extraction_path("artifacts", "debug", "wttj_apply")
DEFAULT_WTTJ_EMAIL_DEBUG_DIR = extraction_path("artifacts", "debug", "wttj_email")
DEFAULT_WTTJ_PROFILE_DIR = extraction_path("runtime", "wttj_playwright_profile")
DEFAULT_GMAIL_CREDENTIALS_FILE = extraction_path("secrets", "credentials.json")
DEFAULT_GMAIL_TOKEN_FILE = extraction_path("secrets", "token.json")
DEFAULT_ENRICHMENT_LIVE_STREAM = extraction_path("data", "jobs", "enrichment_live.jsonl")

# Selectors that are only present in the DOM when the user is logged in to WTTJ.
# Confirmed from captured debug HTMLs: every authenticated job page contains
# data-testid="save-button" (the bookmark icon), which is absent on the
# unauthenticated view that only shows "Sign in".
WTTJ_LOGGED_IN_SELECTORS = [
    "[data-testid='save-button']",
]

# Selectors / text fragments that indicate a WTTJ job listing is no longer
# available.  Checked immediately after page load, before any Apply click.
WTTJ_JOB_UNAVAILABLE_SELECTORS = [
    "p.erfXiH:has-text('Job no longer available')",
    "p:has-text('Job no longer available')",
    "text=Job no longer available",
]
WTTJ_JOB_UNAVAILABLE_TEXT_FRAGMENTS = [
    "job no longer available",
    "cette offre n'est plus disponible",  # French equivalent
    "ce poste n'est plus disponible",
]

# How long (in seconds) to wait for the user to complete login before giving up.
DEFAULT_LOGIN_WAIT_TIMEOUT_S = 120


WTTJ_JOB_URL_HOST_HINTS = [
    "app.welcometothejungle.com",
    "us.welcometothejungle.com",
    "www.welcometothejungle.com",
    "welcometothejungle.com",
    "welcome-to-the-jungle.com",
]

DISALLOWED_EMAIL_LINK_HOST_HINTS = [
    "sendgrid.net",
    "ct.sendgrid.net",
    "email.welcometothejungle.com",
]

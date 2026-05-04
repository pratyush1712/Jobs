"""
Configuration for the resume-tailor pipeline.

Environment variables are loaded from ``extraction/.env`` (relative to the
repo root) using the same light dotenv loader pattern used by the extraction
pipeline.  Variables already set in the shell are never overwritten.

LLM provider
────────────
Uses direct provider API keys via LiteLLM.  Add these to extraction/.env:
  ANTHROPIC_API_KEY   → stages 2 & 3 (Claude)
  GEMINI_API_KEY      → stages 1 & 5 (Gemini)
  OPENAI_API_KEY      → stage 4 (GPT-4o)

Azure credentials are still aliased in case any stage is pointed back at an
Azure deployment (set RESUME_TAILOR_MODEL_Sn=azure/<deployment> to do so).

Per-stage model overrides (optional):
  RESUME_TAILOR_MODEL_S1  …S5   override any individual stage's model string
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR / ".."
JOBS_JSON = BASE_DIR / ".." / "extraction" / "data" / "jobs" / "enrichment_live.jsonl"
RESUMES_DIR = BASE_DIR / "resumes"
READMES_DIR = BASE_DIR / "readmes"
OUTPUT_DIR = BASE_DIR / "output" / "resumes"
LOGS_DIR = BASE_DIR / "output" / "logs"
STATE_FILE = BASE_DIR / "output" / "state.json"


def _load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Minimal .env loader — never overwrites already-set shell variables."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


# ── Azure → LiteLLM env-var aliasing ────────────────────────────────────────
# LiteLLM looks for AZURE_API_KEY / AZURE_API_BASE / AZURE_API_VERSION.
# We map from the existing AZURE_OPENAI_* names used by the extraction pipeline
# so only one set of secrets needs to be kept in .env.


def _azure_base(raw_url: str) -> str:
    """Strip the /openai/... path suffix LiteLLM doesn't want in AZURE_API_BASE."""
    # LiteLLM constructs its own /openai/deployments/... path internally.
    # The base should be just https://<resource>.openai.azure.com/
    for suffix in ("/openai/v1", "/openai"):
        if raw_url.rstrip("/").endswith(suffix):
            return raw_url.rstrip("/")[: -len(suffix)].rstrip("/") + "/"
    return raw_url.rstrip("/") + "/"


_raw_base_url = os.environ.get("AZURE_OPENAI_BASE_URL", "")
os.environ.setdefault("AZURE_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY", ""))
os.environ.setdefault(
    "AZURE_API_BASE", _azure_base(_raw_base_url) if _raw_base_url else ""
)
# Default to the latest GA API version; override via AZURE_API_VERSION if needed.
os.environ.setdefault("AZURE_API_VERSION", "2025-01-01-preview")


# ── Per-stage model routing ───────────────────────────────────────────────────
# Default strategy: best deployment for analysis/rewrite stages,
# fast deployment for execution/scoring stages.
#
# To switch a single stage to a different provider later, just set the
# corresponding env var, e.g.:
#   RESUME_TAILOR_MODEL_S1=gemini/gemini-2.5-pro
#   RESUME_TAILOR_MODEL_S4=openai/gpt-4o

_DEPLOY_BEST: str = os.environ.get("AZURE_OPENAI_DEPLOYMENT_BEST", "")
_DEPLOY_FAST: str = os.environ.get("AZURE_OPENAI_DEPLOYMENT_FAST", "")


def _azure(deployment: str) -> str:
    """Return a LiteLLM Azure model string for the given deployment name."""
    return f"azure/{deployment}" if deployment else ""


# ── Primary models (one per stage) ───────────────────────────────────────────
MODEL_S1_KEYWORD: str = (
    os.environ.get("RESUME_TAILOR_MODEL_S1") or "gemini/gemini-2.5-pro"
)
MODEL_S2_PLAN: str = (
    os.environ.get("RESUME_TAILOR_MODEL_S2") or "anthropic/claude-sonnet-4-5"
)
MODEL_S3_LATEX: str = (
    os.environ.get("RESUME_TAILOR_MODEL_S3") or "anthropic/claude-sonnet-4-5"
)
MODEL_S4_BULLETS: str = os.environ.get("RESUME_TAILOR_MODEL_S4") or "openai/gpt-4o"
MODEL_S5_ATS: str = (
    os.environ.get("RESUME_TAILOR_MODEL_S5") or "gemini/gemini-2.5-flash"
)

# ── Per-stage fallback models ─────────────────────────────────────────────────
# Used automatically if the primary model fails after all retries (bad key,
# provider outage, quota exhausted, etc.).  Each fallback is chosen to be the
# best alternative for that stage's specific task:
#
#   S1 fallback → Claude Sonnet   (strong long-context extraction; thinking ON since
#                                   S1 is a deep-analysis stage)
#   S2 fallback → OpenAI o4-mini  (has chain-of-thought reasoning; Claude is primary)
#   S3 fallback → OpenAI GPT-4o   (solid instruction-following for LaTeX tasks)
#   S4 fallback → Claude Sonnet   (good action-verb variety when GPT-4o is down)
#   S5 fallback → Claude Haiku    (fast + cheap checklist model, mirrors Flash's role)
#
# Set any to an empty string to disable fallback for that stage.
FALLBACK_S1: str = os.environ.get(
    "RESUME_TAILOR_FALLBACK_S1", "anthropic/claude-sonnet-4-5"
)
FALLBACK_S2: str = os.environ.get("RESUME_TAILOR_FALLBACK_S2", "openai/o4-mini")
FALLBACK_S3: str = os.environ.get("RESUME_TAILOR_FALLBACK_S3", "openai/gpt-4o")
FALLBACK_S4: str = os.environ.get(
    "RESUME_TAILOR_FALLBACK_S4", "anthropic/claude-sonnet-4-5"
)
FALLBACK_S5: str = os.environ.get(
    "RESUME_TAILOR_FALLBACK_S5", "anthropic/claude-haiku-3-5"
)

# Token budget for Claude extended thinking (stage 2 only — ignored for Azure).
THINKING_BUDGET_TOKENS: int = int(
    os.environ.get("RESUME_TAILOR_THINKING_BUDGET", "5000")
)

# Request settings
LLM_MAX_RETRIES: int = int(os.environ.get("RESUME_TAILOR_MAX_RETRIES", "3"))
LLM_REQUEST_TIMEOUT: float = float(
    os.environ.get("RESUME_TAILOR_REQUEST_TIMEOUT_S", "180.0")
)


def _optional_temperature(env_var: str, fallback: float) -> float | None:
    """Return temperature from an env var.

    - Env var not set → return ``fallback``.
    - Env var set to empty string → return ``None`` (omit from API call).
    """
    if env_var not in os.environ:
        return fallback
    raw = os.environ[env_var].strip()
    if not raw:
        return None
    return float(raw)


LLM_TEMPERATURE_DEFAULT: float | None = _optional_temperature(
    "RESUME_TAILOR_TEMPERATURE", fallback=0.0
)

# ── Pipeline behaviour ────────────────────────────────────────────────────────
BASE_RESUME_FILE: str | None = "main.tex"
USE_PAST_RESUME_AS_CONTEXT: bool = True
TARGET_STATUSES: set[str] = {"interested", "applied"}
SKIP_EXISTING: bool = True
MAX_JOBS: int | None = None

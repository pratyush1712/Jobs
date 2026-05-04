"""
Enrichment worker: schema, page fetching, LLM calls, retry logic.
Stateless — safe to instantiate once per thread in the enrich pool.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .constants import DEFAULT_ENRICHMENT_LIVE_STREAM, DEFAULT_FAILED_ENRICHMENT_JSONL
from .http_client import make_session
from .models import merge_enrichment_fields
from .utils import clean_text

logger = logging.getLogger(__name__)

AZURE_VARS = [
    "AZURE_OPENAI_BASE_URL",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT_FAST",
    "AZURE_OPENAI_DEPLOYMENT_BEST",
]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrichConfig:
    # Pipeline concurrency
    fetch_workers: int = int(os.getenv("ENRICH_FETCH_WORKERS", "8"))
    enrich_workers: int = int(os.getenv("ENRICH_LLM_WORKERS", "4"))
    queue_max_size: int = int(os.getenv("ENRICH_QUEUE_MAX_SIZE", "20"))

    # Timeouts
    per_record_timeout: float = float(os.getenv("ENRICH_RECORD_TIMEOUT_S", "120"))
    fetch_timeout: float = float(os.getenv("ENRICH_FETCH_TIMEOUT_S", "30"))

    # Prompt / page limits
    page_text_limit: int = int(os.getenv("ENRICH_PAGE_TEXT_LIMIT", "30000"))
    prompt_page_limit: int = int(os.getenv("ENRICH_PROMPT_PAGE_LIMIT", "24000"))

    # LLM
    llm_max_retries: int = int(os.getenv("ENRICH_LLM_MAX_RETRIES", "4"))
    llm_temperature: float = 0.0

    allowed_schemes: frozenset[str] = field(
        default_factory=lambda: frozenset({"http", "https"})
    )

    # Playwright fallback: when the plain HTTP fetch returns fewer than this
    # many characters of page text, re-fetch with a headless browser so that
    # JS-rendered ATS pages (Workday, Oracle, etc.) actually load.
    playwright_fallback: bool = os.getenv(
        "ENRICH_PLAYWRIGHT_FALLBACK", "true"
    ).lower() not in ("0", "false", "no")
    playwright_thin_threshold: int = int(
        os.getenv("ENRICH_PLAYWRIGHT_THIN_THRESHOLD", "200")
    )
    playwright_timeout_ms: int = int(os.getenv("ENRICH_PLAYWRIGHT_TIMEOUT_MS", "30000"))

    # Live streaming: path to a JSONL file that is appended after each record
    # completes enrichment successfully. Empty string disables streaming.
    live_stream_path: str = os.getenv(
        "ENRICH_LIVE_STREAM_PATH", DEFAULT_ENRICHMENT_LIVE_STREAM
    )

    # Failed enrichments: path to a JSONL file that receives records where
    # the page fetch failed or the LLM could not extract meaningful content
    # (page_fetch_error, all_models_failed, etc.). These records are excluded
    # from the live stream and from the master output files.
    # Empty string disables writing failures to a separate file.
    failed_stream_path: str = os.getenv(
        "ENRICH_FAILED_STREAM_PATH", DEFAULT_FAILED_ENRICHMENT_JSONL
    )


_DEFAULT_CFG = EnrichConfig()

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class JobEnrichment(BaseModel):
    summary: str = Field(
        default="",
        description=(
            "2–4 sentence plain-English summary of the role — what the team does, "
            "what the engineer will own, and the key technical focus areas."
        ),
    )
    tech_stack: list[str] = Field(
        default_factory=list,
        description=(
            "Named technologies only: languages, frameworks, libraries, databases, cloud services, "
            "and tools explicitly mentioned in the posting. Each item must be a specific named "
            "product or technology (e.g. 'Python', 'React', 'PostgreSQL', 'AWS Lambda', 'Kubernetes', "
            "'GraphQL'). Never include soft skills, adjectives, or generic descriptions here. "
            "Max 3 words per item. Aim for 5–15 items."
        ),
    )
    resume_keywords: list[str] = Field(
        default_factory=list,
        description=(
            "6–10 exact phrases from the job description that a recruiter or ATS would search for. "
            "These should be domain terms, role-specific jargon, or methodology names that a "
            "candidate should mirror verbatim in their resume and cover letter "
            "(e.g. 'distributed systems', 'REST API design', 'CI/CD pipelines', "
            "'cross-functional collaboration', 'data pipeline', 'production on-call'). "
            "Do not duplicate items already in tech_stack. Focus on concepts, not tools."
        ),
    )
    keywords: list[str] = Field(
        default_factory=list,
        description=(
            "3–6 role/domain category tags for filtering (e.g. 'Backend Engineering', "
            "'Machine Learning', 'DevOps', 'Mobile Development', 'Data Engineering', "
            "'Platform / Infrastructure'). Broader than tech_stack — used for grouping roles."
        ),
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Concrete, resume-listable skills that are explicitly required. "
            "Each item must be short (≤6 words) and suitable as a resume bullet qualifier — "
            "e.g. 'distributed systems design', 'SQL query optimization', 'REST API development', "
            "'Agile sprint planning', 'code review', 'on-call incident response'. "
            "Do NOT copy full sentences from the posting. Do NOT include years-of-experience "
            "statements or degree requirements (those go in `requirements`)."
        ),
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Same format as required_skills but for explicitly preferred/nice-to-have skills. "
            "Short, ≤6 words each."
        ),
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description=(
            "What the person in this role will actually do day-to-day, paraphrased concisely. "
            "Each item should start with an action verb. 5–10 items."
        ),
    )
    requirements: list[str] = Field(
        default_factory=list,
        description=(
            "Eligibility requirements only: degree, years of experience, certifications, "
            "authorization to work. These are gate-keeping criteria, not skills."
        ),
    )
    nice_to_have: list[str] = Field(
        default_factory=list,
        description=(
            "Explicitly 'nice to have' or 'bonus' items not already captured in preferred_skills."
        ),
    )
    compensation: str = Field(
        default="",
        description=(
            "Salary range, equity, or total comp statement exactly as stated. Empty string if not mentioned."
        ),
    )
    benefits: str = Field(default="")
    relocation: str = Field(
        default="", description="'Provided', 'Not provided', or ''."
    )
    visa_sponsorship_policy: str = Field(
        default="", description="'Sponsored', 'Not sponsored', or ''."
    )
    remote_policy: str = Field(
        default="", description="One of: 'Remote', 'Hybrid', 'On-site', or ''."
    )
    employment_type: str = Field(
        default="",
        description="One of: 'Full-time', 'Part-time', 'Contract', 'Internship', or ''.",
    )
    seniority: str = Field(
        default="",
        description=(
            "One of: 'Intern', 'Junior', 'Mid', 'Senior', 'Staff', 'Principal', 'Lead', "
            "'Manager', 'Director', 'VP', 'C-level', or ''. "
            "For 'new grad' or 'entry level' roles use 'Junior'."
        ),
    )
    confidence: str = Field(
        default="low",
        description=(
            "Quality of extraction. Use 'high' when tech_stack has ≥3 items AND required_skills "
            "has ≥2 items AND responsibilities has ≥2 items. Use 'medium' when at least 2 of those "
            "three conditions are met. Use 'low' when the page lacked real job content."
        ),
    )
    confidence_reasoning: str = Field(
        default="",
        description=(
            "Explain why you assigned the confidence level. High: \n"
            "The page contains a clear job description with 3+ technologies, 2+ required skills, and 2+ responsibilities."
            "Medium: \n"
            "The page contains a clear job description with 3+ technologies, 2+ required skills, but less than 2 responsibilities."
            "Low: \n"
            "The page does not contain a clear job description."
            "Other: \n"
            "explain why you assigned the confidence level."
        ),
    )

    @property
    def is_weak(self) -> bool:
        return (
            self.confidence == "low" or not self.tech_stack or not self.required_skills
        )

    @classmethod
    def empty(cls) -> "JobEnrichment":
        return cls()


def _recompute_confidence(enrichment: "JobEnrichment") -> tuple[str, str]:
    """Deterministically compute confidence and reasoning from the actual
    extracted field counts, ignoring whatever the LLM self-reported.

    Rules (must all use the *extracted* lists, not the page text):
      high   — tech_stack ≥ 3  AND  required_skills ≥ 2  AND  responsibilities ≥ 2
      medium — at least 2 of those 3 conditions are met
      low    — fewer than 2 conditions met
    """
    has_tech = len(enrichment.tech_stack) >= 3
    has_skills = len(enrichment.required_skills) >= 2
    has_resp = len(enrichment.responsibilities) >= 2

    conditions_met = sum([has_tech, has_skills, has_resp])

    tech_count = len(enrichment.tech_stack)
    skill_count = len(enrichment.required_skills)
    resp_count = len(enrichment.responsibilities)

    detail = (
        f"tech_stack={tech_count} (need ≥3: {'✓' if has_tech else '✗'}), "
        f"required_skills={skill_count} (need ≥2: {'✓' if has_skills else '✗'}), "
        f"responsibilities={resp_count} (need ≥2: {'✓' if has_resp else '✗'})"
    )

    if conditions_met == 3:
        return "high", f"All three conditions met — {detail}."
    if conditions_met == 2:
        return "medium", f"Two of three conditions met — {detail}."
    return "low", f"Fewer than two conditions met — {detail}."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def azure_configured() -> bool:
    return all(os.getenv(k) for k in AZURE_VARS)


def _attach_error(record: dict[str, Any], message: str) -> dict[str, Any]:
    out = dict(record)
    out.setdefault("raw_listing", {})
    if isinstance(out["raw_listing"], dict):
        out["raw_listing"]["enrichment_error"] = message
    return out


def is_enrichment_failed(record: dict[str, Any]) -> bool:
    """Return True when the record carries a hard enrichment failure marker.

    A failure means the page could not be fetched at all, or all LLM models
    returned nothing useful.  Records with a low-confidence result but at
    least some extracted fields are NOT considered failures here — they are
    weak enrichments and still go into the master output.
    """
    raw = record.get("raw_listing")
    if not isinstance(raw, dict):
        return False
    return bool(raw.get("enrichment_error"))


def _validate_url(url: str, cfg: EnrichConfig = _DEFAULT_CFG) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("Empty URL")
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Unparseable URL: {url!r}") from exc
    if parsed.scheme not in cfg.allowed_schemes:
        raise ValueError(f"Disallowed scheme {parsed.scheme!r} in {url!r}")
    hostname = (parsed.hostname or "").lower()
    blocked = ("localhost", "127.", "0.0.0.0", "169.254.", "::1", "[::1]")
    if any(hostname == b or hostname.startswith(b) for b in blocked):
        raise ValueError(f"Blocked internal hostname {hostname!r}")
    return url


# ---------------------------------------------------------------------------
# Page fetching
# ---------------------------------------------------------------------------


def _extract_jsonld_jobs(soup: BeautifulSoup) -> list[dict]:
    results = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            raw = (tag.string or "").strip()
            if not raw:
                continue
            data = json.loads(raw)
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if isinstance(entry, dict) and "JobPosting" in str(
                    entry.get("@type", "")
                ):
                    results.append(entry)
        except json.JSONDecodeError as exc:
            logger.debug("Skipping malformed JSON-LD block: %s", exc)
    return results


def _parse_html(raw_html: str, base_url: str, cfg: EnrichConfig) -> dict[str, Any]:
    """Parse raw HTML into the page dict used by the enrichment prompt."""
    try:
        soup = BeautifulSoup(raw_html, "html.parser")
    except Exception as exc:
        return {
            "final_url": base_url,
            "page_title": "",
            "page_text": "",
            "jobposting_jsonld": [],
            "error": str(exc),
        }

    page_title = clean_text(
        soup.title.string if soup.title and soup.title.string else ""
    )
    jsonld_jobs = _extract_jsonld_jobs(soup)

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    for sel in ["nav", "footer", "header", "aside", "form"]:
        for tag in soup.select(sel):
            tag.decompose()

    page_text = clean_text(soup.get_text("\n", strip=True))[: cfg.page_text_limit]
    return {
        "final_url": base_url,
        "page_title": page_title,
        "page_text": page_text,
        "jobposting_jsonld": jsonld_jobs,
    }


def _fetch_with_playwright(url: str, cfg: EnrichConfig) -> dict[str, Any]:
    """Re-fetch a page using a headless Chromium browser.

    Used as a fallback when the plain HTTP fetch returns a thin page (bot
    block). Playwright executes JavaScript so ATS vendors like Workday,
    Oracle, and Ashby render their full content.

    Returns the same dict shape as ``fetch_job_page`` so callers are agnostic
    to which method succeeded. Never raises — errors go in the 'error' key.
    """
    base: dict[str, Any] = {
        "final_url": url,
        "page_title": "",
        "page_text": "",
        "jobposting_jsonld": [],
    }
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {**base, "error": "playwright not installed"}

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                )
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=cfg.playwright_timeout_ms,
                )
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except Exception:
                    pass
                final_url = page.url
                html = page.content()
            finally:
                browser.close()
        result = _parse_html(html, final_url, cfg)
        result["_fetch_method"] = "playwright"
        return result
    except Exception as exc:
        logger.debug("Playwright fetch failed for %s: %s", url, exc)
        return {
            **base,
            "error": f"playwright_error: {exc}",
            "_fetch_method": "playwright",
        }


def fetch_job_page(url: str, cfg: EnrichConfig = _DEFAULT_CFG) -> dict[str, Any]:
    """Fetch and parse a job page. Never raises — errors go in the 'error' key.

    Strategy:
    1. Plain HTTP fetch with browser-like headers (fast, no JS).
    2. If the result is thin (bot block), fall back to headless Playwright so
       JS-rendered ATS pages (Workday, Oracle, Ashby, etc.) actually load.
    """
    base: dict[str, Any] = {
        "final_url": url,
        "page_title": "",
        "page_text": "",
        "jobposting_jsonld": [],
    }
    session = make_session()
    try:
        resp = session.get(url, timeout=cfg.fetch_timeout, allow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.debug("HTTP fetch failed for %s: %s", url, exc)
        if cfg.playwright_fallback:
            return _fetch_with_playwright(url, cfg)
        return {**base, "error": str(exc), "_fetch_method": "http"}

    content_type = (resp.headers.get("content-type") or "").lower()
    if "html" not in content_type:
        return {
            **base,
            "final_url": str(resp.url),
            "page_text": resp.text[: cfg.page_text_limit],
            "_fetch_method": "http",
        }

    result = _parse_html(resp.text, str(resp.url), cfg)
    result["_fetch_method"] = "http"
    page_text = result.get("page_text", "")

    if len(page_text) < cfg.playwright_thin_threshold:
        logger.debug(
            "Thin page (%d chars) for %s — trying Playwright.", len(page_text), url
        )
        if cfg.playwright_fallback:
            pw_result = _fetch_with_playwright(url, cfg)
            # Only use Playwright result if it actually has more content.
            if len(pw_result.get("page_text", "")) > len(page_text):
                return pw_result

    return result


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a precise job-posting data extractor. The output will be used by a job \
seeker to tailor their resume and cover letter, so accuracy and specificity are \
critical.

## Core rules
- Extract only what is explicitly stated. Do not infer or invent.
- Use "" or [] when a field is not mentioned.
- Obey the allowed values for enum fields exactly as described in the schema.

## Field-specific guidance

**tech_stack** — Named technologies only. Pull every specific language, framework, \
library, database, cloud service, platform, and tool mentioned. Be exhaustive. \
Never include soft skills, verbs, or adjectives. Good: "Python", "React", \
"PostgreSQL", "AWS S3", "Kubernetes", "GraphQL". Bad: "programming", "teamwork", \
"experience with databases".

**resume_keywords** — Phrases the candidate should mirror verbatim in their resume \
to pass ATS and resonate with the hiring manager. Pick domain terms, methodology \
names, and role-specific jargon that are NOT already captured in tech_stack. \
Good: "distributed systems", "REST API design", "CI/CD pipelines", \
"production on-call", "cross-functional collaboration". Bad: "Python" \
(already in tech_stack), "good communication" (too generic).

**keywords** — 3–6 broad category tags for grouping/filtering roles, not for \
the resume itself. Examples: "Backend Engineering", "Machine Learning", \
"Data Engineering", "Platform / Infrastructure", "Mobile Development".

**required_skills** — Short (≤6 words each), resume-listable, concrete skills. \
Each item should be something you could put in a "Skills" section or as a \
bullet qualifier. Never copy full sentences. Never include degree or YOE \
requirements (those go in `requirements`). Good: "distributed systems design", \
"SQL query optimization", "REST API development", "code review". \
Bad: "2+ years of experience with Python in a production environment".

**preferred_skills** — Same concise format as required_skills, but for \
explicitly preferred/bonus skills.

**responsibilities** — What the person actually does day-to-day. Start each \
item with an action verb. Paraphrase; do not copy verbatim. 5–10 items.

**requirements** — Gate-keeping criteria only: degree level, years of \
experience, certifications, work authorization. Not skills.

**seniority** — Map "new grad", "entry level", "university hire" → "Junior".

**confidence** — Follow the schema description exactly. "high" requires \
tech_stack ≥3, required_skills ≥2, AND responsibilities ≥2. Otherwise \
"medium" (2 of 3 conditions met) or "low" (page lacked real job content).

**confidence-reasoning** — Explain why you assigned the confidence level.
High: The page contains a clear job description with 3+ technologies, 2+ required skills, and 2+ responsibilities.
Medium: The page contains a clear job description with 3+ technologies, 2+ required skills, but less than 2 responsibilities.
Low: The page does not contain a clear job description.
Other: Explain why you assigned the confidence level.

"""


def build_messages(
    record: dict[str, Any],
    page: dict[str, Any],
    cfg: EnrichConfig = _DEFAULT_CFG,
) -> list[dict[str, str]]:
    ctx = {
        k: record.get(k)
        for k in ["company", "job_title", "location", "job_url", "source"]
    }
    payload = json.dumps(page, ensure_ascii=False)[: cfg.prompt_page_limit]
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"## Job Record\n{json.dumps(ctx, ensure_ascii=False, indent=2)}\n\n"
                f"## Fetched Page\n{payload}"
            ),
        },
    ]


# ---------------------------------------------------------------------------
# LLM call with tenacity retry
# ---------------------------------------------------------------------------


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (RateLimitError, APITimeoutError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return False


def _maybe_honor_retry_after(exc: BaseException) -> None:
    if isinstance(exc, RateLimitError) and exc.response is not None:
        raw = exc.response.headers.get("Retry-After") or exc.response.headers.get(
            "x-ratelimit-reset-requests"
        )
        if raw:
            try:
                secs = float(raw)
                if 0 < secs <= 120:
                    logger.info("Rate limited — sleeping Retry-After: %.1fs", secs)
                    time.sleep(secs)
            except (ValueError, TypeError):
                pass


def _strict_json_schema() -> dict:
    """Return the JobEnrichment JSON schema with the fields required by Azure
    OpenAI strict mode: ``additionalProperties: false`` at the root and every
    property listed in ``required`` (Pydantic omits both when all fields have
    defaults)."""
    schema = JobEnrichment.model_json_schema()
    # Azure strict mode requires additionalProperties: false at every object level.
    schema["additionalProperties"] = False
    # All properties must appear in "required" for strict mode.
    schema.setdefault("required", list(schema.get("properties", {}).keys()))
    return schema


# Build once at import time — the schema is static.
_STRICT_SCHEMA = _strict_json_schema()


def _call_model(
    client: OpenAI,
    model: str,
    messages: list[dict],
    cfg: EnrichConfig = _DEFAULT_CFG,
) -> JobEnrichment:

    @retry(
        # Only retry transient/server errors. 400 (bad request) and 404
        # (deployment not found) are non-retryable and must not loop.
        retry=retry_if_exception_type(
            (RateLimitError, APITimeoutError, APIConnectionError)
        ),
        wait=wait_exponential_jitter(initial=2, max=60, jitter=5),
        stop=stop_after_attempt(cfg.llm_max_retries),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _attempt() -> JobEnrichment:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "JobEnrichment",
                        "strict": True,
                        "schema": _STRICT_SCHEMA,
                    },
                },
                temperature=cfg.llm_temperature,
            )
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            _maybe_honor_retry_after(exc)
            raise
        except APIStatusError as exc:
            # 5xx → retryable server error; 4xx → permanent failure, don't retry.
            if exc.status_code >= 500:
                raise
            logger.error(
                "Non-retryable API error (status=%d) model=%s: %s",
                exc.status_code,
                model,
                exc,
            )
            # Raise a plain ValueError so tenacity does NOT retry this.
            raise ValueError(
                f"Non-retryable API error {exc.status_code}: {exc}"
            ) from exc

        content = (
            (resp.choices[0].message.content or "").strip() if resp.choices else ""
        )
        if not content:
            finish = resp.choices[0].finish_reason if resp.choices else "unknown"
            raise ValueError(f"Empty model response (finish_reason={finish!r})")

        try:
            return JobEnrichment.model_validate_json(content)
        except ValidationError as exc:
            logger.warning("Pydantic validation failed for model %s: %s", model, exc)
            raise ValueError(f"Schema validation failed: {exc}") from exc

    return _attempt()


# ---------------------------------------------------------------------------
# EnrichWorker — one instance per enrich thread
# ---------------------------------------------------------------------------


class EnrichWorker:
    """
    Stateless enrichment worker. Instantiated once per enrich thread.
    Holds a single OpenAI client (thread-safe for concurrent calls).
    """

    def __init__(self, cfg: EnrichConfig = _DEFAULT_CFG) -> None:
        self.cfg = cfg
        self._client = self._make_client()
        fast = os.environ.get("AZURE_OPENAI_DEPLOYMENT_FAST", "").strip()
        best = os.environ.get("AZURE_OPENAI_DEPLOYMENT_BEST", "").strip()
        if not fast or not best:
            raise RuntimeError(
                "AZURE_OPENAI_DEPLOYMENT_FAST and AZURE_OPENAI_DEPLOYMENT_BEST "
                "must be set before creating an EnrichWorker."
            )
        self._fast = fast
        self._best = best

    @staticmethod
    def _make_client() -> OpenAI:
        return OpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            base_url=os.environ["AZURE_OPENAI_BASE_URL"],
            max_retries=0,  # tenacity owns retry logic
            timeout=60.0,
        )

    def enrich_with_page(
        self,
        record: dict[str, Any],
        page: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Given a pre-fetched page dict, run the LLM enrichment and return
        the merged record. Never raises — returns record with error attached.
        """
        # If page fetch produced nothing usable, bail early
        if (
            page.get("error")
            and not page.get("page_text")
            and not page.get("jobposting_jsonld")
        ):
            logger.warning(
                "Skipping LLM for %s — page fetch failed: %s",
                record.get("job_url"),
                page["error"],
            )
            return _attach_error(record, f"page_fetch_error: {page['error']}")

        messages = build_messages(record, page, self.cfg)
        extracted: JobEnrichment | None = None

        try:
            extracted = _call_model(self._client, self._fast, messages, self.cfg)
        except Exception as exc:
            logger.warning(
                "Fast model (%s) failed for %s: %s",
                self._fast,
                record.get("job_url"),
                exc,
            )

        if (extracted is None or extracted.is_weak) and self._best != self._fast:
            logger.debug("Falling back to best model for %s", record.get("job_url"))
            try:
                extracted2 = _call_model(self._client, self._best, messages, self.cfg)
                if extracted is None or not extracted2.is_weak:
                    extracted = extracted2
            except Exception as exc:
                logger.warning(
                    "Best model (%s) failed for %s: %s",
                    self._best,
                    record.get("job_url"),
                    exc,
                )

        if extracted is None:
            return _attach_error(record, "all_models_failed")

        # Recompute confidence deterministically from the actual extracted
        # field counts — the LLM frequently mis-labels its own output.
        recomputed_confidence, recomputed_reasoning = _recompute_confidence(extracted)
        extracted.confidence = recomputed_confidence
        extracted.confidence_reasoning = recomputed_reasoning

        enrichment = extracted.model_dump()
        if page.get("page_title"):
            enrichment.setdefault("page_title", page["page_title"])

        return merge_enrichment_fields(record, enrichment)

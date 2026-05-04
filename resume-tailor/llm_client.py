"""
LiteLLM wrapper for the resume-tailor pipeline.

All LLM calls go through ``call_llm``.  Pass a ``stage`` literal to select
the model optimised for that pipeline stage:

  "s1" → Gemini 2.5 Pro         (keyword extraction — long-context analysis)
  "s2" → Claude Sonnet 4.5 +    (rewrite plan — extended thinking enabled)
          extended thinking
  "s3" → Claude Sonnet 4.5      (LaTeX rewrite — format-preserving execution)
  "s4" → GPT-4o                 (bullet polish — action-verb variety)
  "s5" → Gemini 2.5 Flash       (ATS check — fast structured scoring)

Provider routing is handled automatically by LiteLLM based on the model
string prefix.  Set credentials in extraction/.env:
  ANTHROPIC_API_KEY   → stages 2 & 3
  GEMINI_API_KEY      → stages 1 & 5
  OPENAI_API_KEY      → stage 4

Retry policy:
  - Retries on rate-limit, connection, and timeout errors with exponential
    back-off + jitter via tenacity.
  - 4xx non-rate-limit errors are NOT retried (permanent failures).
  - Retry-After headers are honoured when present.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

import litellm
from config import (
    FALLBACK_S1,
    FALLBACK_S2,
    FALLBACK_S3,
    FALLBACK_S4,
    FALLBACK_S5,
    LLM_MAX_RETRIES,
    LLM_REQUEST_TIMEOUT,
    LLM_TEMPERATURE_DEFAULT,
    MODEL_S1_KEYWORD,
    MODEL_S2_PLAN,
    MODEL_S3_LATEX,
    MODEL_S4_BULLETS,
    MODEL_S5_ATS,
    THINKING_BUDGET_TOKENS,
)
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    RateLimitError,
    Timeout,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

# Suppress LiteLLM's verbose default logging — we manage our own.
litellm.suppress_debug_info = True

# Valid stage identifiers for type checking.
Stage = Literal["s1", "s2", "s3", "s4", "s5"]

# Map each stage to its primary model and its fallback model.
_STAGE_MODELS: dict[Stage, str] = {
    "s1": MODEL_S1_KEYWORD,
    "s2": MODEL_S2_PLAN,
    "s3": MODEL_S3_LATEX,
    "s4": MODEL_S4_BULLETS,
    "s5": MODEL_S5_ATS,
}

_STAGE_FALLBACKS: dict[Stage, str] = {
    "s1": FALLBACK_S1,
    "s2": FALLBACK_S2,
    "s3": FALLBACK_S3,
    "s4": FALLBACK_S4,
    "s5": FALLBACK_S5,
}

# Stages where extended thinking should be active when the model is Anthropic.
# S1 (keyword extraction) and S2 (rewrite plan) are both deep-analysis stages
# that benefit from Claude's extended thinking.
_THINKING_STAGES: frozenset[str] = frozenset({"s1", "s2"})


def _thinking_enabled(stage: "Stage", model: str) -> bool:
    """Return True when ``stage`` is a thinking stage and ``model`` is Anthropic."""
    return stage in _THINKING_STAGES and model.startswith("anthropic/")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _maybe_honor_retry_after(exc: BaseException) -> None:
    """Sleep for the Retry-After duration advertised in a 429 response."""
    if not isinstance(exc, RateLimitError):
        return
    response = getattr(exc, "response", None)
    if response is None:
        return
    headers = getattr(response, "headers", {}) or {}
    raw = headers.get("Retry-After") or headers.get("x-ratelimit-reset-requests")
    if raw:
        try:
            secs = float(raw)
            if 0 < secs <= 120:
                logger.info("Rate-limited — honouring Retry-After: %.1fs", secs)
                time.sleep(secs)
        except (ValueError, TypeError):
            pass


def _extract_text_content(resp: litellm.ModelResponse) -> str:
    """Extract plain text from a LiteLLM response.

    For standard responses ``content`` is a string.  For Claude extended-
    thinking responses, ``content`` may be a list of typed blocks; we pick
    the first ``"text"`` block and ignore ``"thinking"`` blocks.
    """
    if not resp.choices:
        return ""

    raw = resp.choices[0].message.content

    if isinstance(raw, str):
        return raw.strip()

    # Extended-thinking responses arrive as a list of content blocks.
    if isinstance(raw, list):
        for block in raw:
            block_type = getattr(block, "type", None) or (
                block.get("type") if isinstance(block, dict) else None
            )
            if block_type == "text":
                text = getattr(block, "text", None) or (
                    block.get("text") if isinstance(block, dict) else None
                )
                if text:
                    return str(text).strip()

    return ""


# ---------------------------------------------------------------------------
# Internal: single-model call with tenacity retries
# ---------------------------------------------------------------------------


def _call_model(
    model: str,
    messages: list[dict[str, str]],
    stage: Stage,
    max_completion_tokens: int,
) -> str:
    """Attempt to call ``model`` with retries. Raises on final failure."""
    is_thinking = _thinking_enabled(stage, model)

    @retry(
        retry=retry_if_exception_type((RateLimitError, Timeout, APIConnectionError)),
        wait=wait_exponential_jitter(initial=2, max=60, jitter=5),
        stop=stop_after_attempt(LLM_MAX_RETRIES),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _attempt() -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_completion_tokens,
            "timeout": LLM_REQUEST_TIMEOUT,
        }

        if is_thinking:
            # Extended thinking requires temperature=1.0 (Anthropic API rule).
            kwargs["temperature"] = 1.0
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": THINKING_BUDGET_TOKENS,
            }
        elif LLM_TEMPERATURE_DEFAULT is not None:
            kwargs["temperature"] = LLM_TEMPERATURE_DEFAULT

        try:
            resp = litellm.completion(**kwargs)
        except (RateLimitError, Timeout, APIConnectionError) as exc:
            _maybe_honor_retry_after(exc)
            raise
        except APIError as exc:
            status_code: int = getattr(exc, "status_code", 0) or 0
            if status_code >= 500:
                raise  # server error → tenacity will retry
            logger.error(
                "Non-retryable API error (status=%d, model=%s, stage=%s): %s",
                status_code,
                model,
                stage,
                exc,
            )
            raise ValueError(f"Non-retryable API error {status_code}: {exc}") from exc

        content = _extract_text_content(resp)
        if not content:
            finish = resp.choices[0].finish_reason if resp.choices else "unknown"
            raise RuntimeError(
                f"Empty model response "
                f"(stage={stage!r}, model={model!r}, finish_reason={finish!r})"
            )

        logger.debug(
            "LLM call OK  stage=%s  model=%s  thinking=%s  tokens_used=%s",
            stage,
            model,
            is_thinking,
            getattr(resp.usage, "total_tokens", "n/a"),
        )
        return content

    return _attempt()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def call_llm(
    prompt: str,
    *,
    stage: Stage,
    max_completion_tokens: int = 8000,
    system: str | None = None,
) -> str:
    """Call the model assigned to ``stage`` via LiteLLM and return the response.

    If the primary model fails after all retries, the call is transparently
    retried once on ``FALLBACK_MODEL`` (default: anthropic/claude-sonnet-4-5).
    If the primary model IS the fallback, no second attempt is made.

    Args:
        prompt:               User-turn content.
        stage:                Pipeline stage — determines which model to use.
                              One of: "s1", "s2", "s3", "s4", "s5".
        max_completion_tokens: Upper bound on the model's response length.
                              For stage 2 with Claude, must exceed THINKING_BUDGET_TOKENS.
        system:               Optional system message.  Omitted when ``None``.

    Returns:
        The model's response text, stripped of leading/trailing whitespace.

    Raises:
        EnvironmentError: Model string is empty or required API key is missing.
        RuntimeError:     Both primary and fallback models return empty responses.
        ValueError:       Non-retryable 4xx API error on both models.
    """
    primary = _STAGE_MODELS[stage]
    if not primary:
        raise EnvironmentError(
            f"Model for stage {stage!r} is not configured. "
            f"Set RESUME_TAILOR_MODEL_{stage.upper()} in extraction/.env."
        )

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    fallback = _STAGE_FALLBACKS[stage]

    try:
        return _call_model(primary, messages, stage, max_completion_tokens)
    except Exception as primary_exc:
        # Skip fallback if it is empty or identical to the primary (no point
        # calling the same model/provider that just failed).
        if not fallback or fallback == primary:
            raise

        logger.warning(
            "Primary model failed (stage=%s, model=%s): %s — falling back to %s",
            stage,
            primary,
            primary_exc,
            fallback,
        )
        return _call_model(fallback, messages, stage, max_completion_tokens)

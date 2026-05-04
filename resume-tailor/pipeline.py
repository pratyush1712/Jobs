import logging
import re

from config import LOGS_DIR, OUTPUT_DIR, USE_PAST_RESUME_AS_CONTEXT
from job_context import build_jd_block
from llm_client import call_llm
from prompts import (
    stage1_keyword_analysis,
    stage2_rewrite_plan,
    stage3_latex_rewrite,
    stage4_bullet_polish,
    stage5_ats_check,
)
from resume_selector import get_past_resume, select_base_resume

logger = logging.getLogger(__name__)


def safe_filename(job: dict) -> str:
    company = re.sub(r"[^\w]", "_", job.get("company", "unknown"))
    title = re.sub(r"[^\w]", "_", job.get("job_title", "role"))
    jid = job.get("id", "")[:8]
    return f"{company}__{title}__{jid}"


def run_pipeline(job: dict, readme_context: str) -> dict:
    name = safe_filename(job)
    job_output_dir = OUTPUT_DIR / name
    job_output_dir.mkdir(parents=True, exist_ok=True)
    log_dir = LOGS_DIR / name
    log_dir.mkdir(parents=True, exist_ok=True)

    # ── Load resumes ────────────────────────────────────────────────────────
    base_file, resume_latex = select_base_resume(job)
    logger.info("[%s] Base resume: %s", name, base_file)

    past_resume_context = ""
    if USE_PAST_RESUME_AS_CONTEXT:
        past = get_past_resume(job.get("company", ""))
        if past:
            past_file, past_latex = past
            past_resume_context = (
                f"\n\n--- PAST RESUME FOR THIS COMPANY ({past_file}) ---\n"
                f"(Use this only as reference for tone and past tailoring decisions. "
                f"Do NOT copy it — base all changes on main.tex)\n{past_latex}"
            )
            logger.info("[%s] Past resume found: %s", name, past_file)

    jd_block = build_jd_block(job)
    full_readme = readme_context + past_resume_context

    # ── Stage 1: Keyword Analysis (Gemini 2.5 Pro) ──────────────────────────
    logger.info("[%s] Stage 1: Keyword extraction — Gemini 2.5 Pro", name)
    s1_prompt = stage1_keyword_analysis(jd_block, resume_latex, full_readme)
    keyword_table = call_llm(s1_prompt, stage="s1", max_completion_tokens=6000)
    (log_dir / "stage1_keywords.md").write_text(keyword_table, encoding="utf-8")

    # ── Stage 2: Rewrite Plan (Claude Sonnet 4.5 + extended thinking) ───────
    logger.info("[%s] Stage 2: Rewrite plan — Claude extended thinking", name)
    s2_prompt = stage2_rewrite_plan(jd_block, resume_latex, keyword_table)
    # max_completion_tokens must exceed THINKING_BUDGET_TOKENS (default 5000).
    rewrite_plan = call_llm(s2_prompt, stage="s2", max_completion_tokens=12000)
    (log_dir / "stage2_plan.md").write_text(rewrite_plan, encoding="utf-8")

    # ── Stage 3: LaTeX Rewrite (Claude Sonnet 4.5, thinking OFF) ────────────
    logger.info("[%s] Stage 3: LaTeX rewrite — Claude Sonnet", name)
    s3_prompt = stage3_latex_rewrite(resume_latex, rewrite_plan)
    new_latex = call_llm(s3_prompt, stage="s3", max_completion_tokens=16000)
    # Strip any accidental markdown code fences the model may emit.
    new_latex = re.sub(r"^```(?:latex)?\n?", "", new_latex.strip())
    new_latex = re.sub(r"\n?```$", "", new_latex.strip())

    # ── Stage 4: Bullet Polish (GPT-4o) ─────────────────────────────────────
    logger.info("[%s] Stage 4: Bullet polish — GPT-4o", name)
    s4_prompt = stage4_bullet_polish(new_latex)
    polished_latex = call_llm(s4_prompt, stage="s4", max_completion_tokens=16000)
    polished_latex = re.sub(r"^```(?:latex)?\n?", "", polished_latex.strip())
    polished_latex = re.sub(r"\n?```$", "", polished_latex.strip())

    tex_path = job_output_dir / f"resume_{name}.tex"
    tex_path.write_text(polished_latex, encoding="utf-8")
    logger.info("[%s] Saved: %s", name, tex_path)

    # ── Stage 5: ATS Self-Check (Gemini 2.5 Flash) ──────────────────────────
    logger.info("[%s] Stage 5: ATS check — Gemini 2.5 Flash", name)
    s5_prompt = stage5_ats_check(polished_latex, jd_block, keyword_table)
    ats_report = call_llm(s5_prompt, stage="s5", max_completion_tokens=3000)
    (log_dir / "stage5_ats_check.md").write_text(ats_report, encoding="utf-8")

    score_match = re.search(r"ATS Match Score[:\s]+([0-9]+)", ats_report, re.IGNORECASE)
    ats_score = int(score_match.group(1)) if score_match else None

    return {
        "job_id": job.get("id"),
        "company": job.get("company"),
        "job_title": job.get("job_title"),
        "base_resume": base_file,
        "tex_path": str(tex_path),
        "ats_score": ats_score,
        "log_dir": str(log_dir),
    }

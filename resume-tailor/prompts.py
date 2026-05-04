def stage1_keyword_analysis(
    jd_block: str, resume_latex: str, readme_context: str
) -> str:
    return f"""You are an expert ATS analyst and technical recruiter specializing in software engineering and product roles.

I will give you:
1. My full background (from personal README files)
2. My current LaTeX resume source
3. A structured job description

Your tasks:
- Extract the top 15-20 ATS-critical keywords and phrases from the JD (hard skills, tools, frameworks, methodologies, buzzwords)
- Categorize each as: [PRESENT] / [MISSING] / [WEAK]
- For MISSING/WEAK: suggest which resume section to target (Summary, Skills, Experience, Projects)
- Flag any keyword that would be dishonest given my actual background: mark [DO NOT ADD]
- Output a clean markdown table: Keyword | Status | Target Section | Notes

IMPORTANT: Do NOT rewrite anything. Analysis only.

--- MY BACKGROUND (README FILES) ---
{readme_context}

--- MY RESUME (LaTeX source) ---
{resume_latex}

--- JOB DESCRIPTION ---
{jd_block}
"""


def stage2_rewrite_plan(jd_block: str, resume_latex: str, keyword_table: str) -> str:
    return f"""Using the keyword gap analysis below, create a precise line-by-line rewrite plan.

For each section that needs changes:
- Quote the ORIGINAL LaTeX line(s) verbatim
- Write the PROPOSED replacement line(s)
- One-sentence reason why this improves ATS alignment

Hard rules:
- Do NOT fabricate experience, tools, or projects not in my background
- Do NOT change section headers, newcommands, usepackage, or any formatting macros
- Do NOT touch sections with no keyword gaps
- Preserve all custom environments (resumeItem, resumeSubheading, cventry, etc.) exactly
- Natural integration only, no keyword stuffing

Output format per change:
SECTION: [section name]
ORIGINAL:
[original line(s)]

PROPOSED:
[new line(s)]

REASON: [one sentence]

--- KEYWORD GAP TABLE ---
{keyword_table}

--- CURRENT RESUME (LaTeX) ---
{resume_latex}

--- JOB DESCRIPTION ---
{jd_block}
"""


def stage3_latex_rewrite(resume_latex: str, rewrite_plan: str) -> str:
    return f"""You are a LaTeX formatting expert. Apply the rewrite plan below to the original LaTeX resume.

Critical rules:
- Output the COMPLETE .tex file with no truncation and no placeholders like percent rest unchanged
- Preserve every usepackage, newcommand, definecolor, and preamble line exactly as-is
- Do NOT change margins, fonts, spacing, column layout, or any visual formatting
- Do NOT add or remove sections
- Only modify the specific lines identified in the rewrite plan
- Output raw LaTeX ONLY with no markdown, no explanation, no code fences

--- ORIGINAL RESUME (LaTeX) ---
{resume_latex}

--- REWRITE PLAN ---
{rewrite_plan}
"""


def stage4_bullet_polish(resume_latex: str) -> str:
    return f"""You are an elite resume writer known for punchy, metric-driven bullet points.

Your task: rewrite ONLY the \\resumeItem{{...}} and \\item{{...}} bullets in the LaTeX below.
Do NOT touch anything else — no preamble, no section headers, no formatting macros.

Rules for each bullet:
- Start with a strong, varied action verb (never repeat the same verb twice)
- Lead with impact: quantify with numbers, percentages, or scale wherever the
  existing bullet already implies a metric — do NOT fabricate new numbers
- Keep each bullet to one line (≤ 120 characters of content inside the braces)
- Preserve the exact LaTeX command and braces: \\resumeItem{{NEW CONTENT HERE}}
- If a bullet is already strong, leave it exactly as-is

Output the COMPLETE .tex file with every line preserved except the polished bullets.
No markdown, no explanation, no code fences — raw LaTeX only.

--- RESUME (LaTeX) ---
{resume_latex}
"""


def stage5_ats_check(resume_latex: str, jd_block: str, keyword_table: str) -> str:
    return f"""Review this tailored LaTeX resume against the job description and keyword analysis.

Check each item and output PASS / WARN / FAIL:
1. Are all [MISSING] keywords from the analysis now present?
2. Any keyword stuffing? (same phrase 3+ times)
3. Does the summary/objective directly echo the role title?
4. Any LaTeX commands that break ATS PDF parsing? (multi-column layout, tables for structure, special chars)
5. Consistency: does experience timeline make sense?

Then give:
- ATS Match Score: X/100
- Top 3 remaining improvement suggestions

--- FINAL RESUME (LaTeX) ---
{resume_latex}

--- JOB DESCRIPTION ---
{jd_block}

--- ORIGINAL KEYWORD GAP TABLE ---
{keyword_table}
"""

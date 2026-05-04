"""Browser resolver for real WTTJ Apply modal links."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from .constants import (
    APPLY_BUTTON_SELECTORS,
    ATS_OR_JOB_HINTS,
    BAD_URL_HINTS,
    DEFAULT_LOGIN_WAIT_TIMEOUT_S,
    DEFAULT_WTTJ_DEBUG_DIR,
    DEFAULT_WTTJ_PROFILE_DIR,
    MODAL_OR_DRAWER_SELECTORS,
    WTTJ_JOB_UNAVAILABLE_SELECTORS,
    WTTJ_JOB_UNAVAILABLE_TEXT_FRAGMENTS,
    WTTJ_LOGGED_IN_SELECTORS,
)
from .utils import clean_space, write_json, is_wttj_job_detail_url, is_sendgrid_tracking_url, is_wttj_email_control_url

try:
    from playwright.sync_api import Page, sync_playwright
except Exception:  # pragma: no cover
    Page = Any  # type: ignore
    sync_playwright = None  # type: ignore


@dataclass
class CandidateLink:
    url: str
    text: str = ""
    context: str = ""
    source: str = "html_anchor"
    score: int = 0


@dataclass
class WTTJResolveResult:
    input_url: str
    company: str = ""
    title: str = ""
    page_url_before_click: str = ""
    page_url_after_click: str = ""
    clicked_selector: str = ""
    modal_detected: bool = False
    selected_url: str = ""
    candidates: list[dict[str, Any]] | None = None
    error: str = ""
    debug_screenshot_after: str = ""
    job_unavailable: bool = False
    resolved_wttj_url: str = ""
    """The clean WTTJ /jobs/ URL the browser landed on after following any
    redirects (e.g. SendGrid → WTTJ), with tracking query params stripped.
    Empty when the input was already a direct WTTJ URL or navigation failed."""


def hostname(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""


def is_wttj_url(url: str) -> bool:
    host = hostname(url)
    return "welcometothejungle" in host or "welcome-to-the-jungle" in host


def is_bad_url(url: str) -> bool:
    lower = (url or "").lower()
    return not lower or lower in {"#", "/"} or any(h in lower for h in BAD_URL_HINTS)


def score_candidate(candidate: CandidateLink, company: str = "") -> int:
    lower_url = candidate.url.lower()
    lower_text = candidate.text.lower()
    lower_context = candidate.context.lower()
    if is_bad_url(candidate.url):
        return -999
    score = 0
    if any(h in lower_url for h in ATS_OR_JOB_HINTS):
        score += 60
    if "or apply on" in lower_context or ("apply on" in lower_context and "website" in lower_context):
        score += 100
    if "website" in lower_text or "website" in lower_context:
        score += 20
    if company and company.lower() in lower_context:
        score += 15
    if is_wttj_url(candidate.url):
        score -= 120
    return score


def extract_candidates_from_html(raw_html: str, company: str = "") -> list[CandidateLink]:
    soup = BeautifulSoup(raw_html or "", "html.parser")
    out: list[CandidateLink] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = clean_space(a.get("href"))
        if not url or url in seen:
            continue
        seen.add(url)
        text = clean_space(a.get_text(" ", strip=True))
        context = clean_space(a.parent.get_text(" ", strip=True) if a.parent else text)
        c = CandidateLink(url=url, text=text, context=context)
        c.score = score_candidate(c, company)
        out.append(c)
    return sorted(out, key=lambda c: c.score, reverse=True)


def is_logged_in(page: Page) -> bool:
    """Return True if any known logged-in indicator is visible on the page."""
    for selector in WTTJ_LOGGED_IN_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=500):
                return True
        except Exception:
            pass
    return False


def wait_for_login(page: Page, timeout_s: int = DEFAULT_LOGIN_WAIT_TIMEOUT_S) -> bool:
    """
    Block until the page shows a logged-in state, or until *timeout_s* seconds
    have elapsed.  Prints a one-time prompt so the operator knows to log in.

    The Playwright persistent profile is separate from your regular browser, so
    you must log in inside the Playwright browser window the first time.  After
    that the session is cached in the profile directory and future runs skip this
    gate entirely.

    Each poll tick also reloads the page so that a login completed on the WTTJ
    login page (after a redirect) is reflected on the job page we care about.

    Returns True when login is detected, False when the timeout expires.
    """
    if is_logged_in(page):
        return True

    original_url = page.url
    print(
        f"\n[WTTJ] Not logged in — please sign in to Welcome to the Jungle in the "
        f"browser window that just opened.\n"
        f"       The Playwright browser has its own session separate from Chrome.\n"
        f"       Log in there, then the script will continue automatically.\n"
        f"       Waiting up to {timeout_s}s …",
        flush=True,
    )
    deadline = time.time() + timeout_s
    poll_interval_s = 2.0
    while time.time() < deadline:
        time.sleep(poll_interval_s)
        # If the login flow navigated away from the job page, reload it so we
        # can detect the save-button that only appears on authenticated job pages.
        try:
            if not is_wttj_job_detail_url(page.url):
                page.goto(original_url, wait_until="domcontentloaded", timeout=15000)
        except Exception:
            pass
        if is_logged_in(page):
            print("[WTTJ] Login detected — continuing.", flush=True)
            return True

    print(f"[WTTJ] Login not detected within {timeout_s}s — proceeding anyway.", flush=True)
    return False


def _has_apply_button(page: Page) -> bool:
    """Return True if an explicit Apply button is present in the DOM."""
    for selector in APPLY_BUTTON_SELECTORS:
        try:
            if page.locator(selector).first.count() > 0:
                return True
        except Exception:
            pass
    return False


def detect_job_unavailable(page: Page) -> bool:
    """Return True if the WTTJ page shows a 'Job no longer available' banner.

    Checks via Playwright selectors first (fast), then falls back to a
    plain-text scan of the page body as a safety net for markup changes.
    """
    for selector in WTTJ_JOB_UNAVAILABLE_SELECTORS:
        try:
            if page.locator(selector).first.count() > 0:
                return True
        except Exception:
            pass
    try:
        body_text = page.inner_text("body").lower()
        if any(fragment in body_text for fragment in WTTJ_JOB_UNAVAILABLE_TEXT_FRAGMENTS):
            return True
    except Exception:
        pass
    return False


def detect_job_unavailable_in_html(html: str) -> bool:
    """Return True if raw HTML contains a 'Job no longer available' banner.

    Used after the Apply modal opens to catch cases where the job card on the
    WTTJ page (or embedded Otta panel) shows the banner without navigating away.
    Operates on already-fetched HTML so no extra page visit is required.
    """
    lower = (html or "").lower()
    return any(fragment in lower for fragment in WTTJ_JOB_UNAVAILABLE_TEXT_FRAGMENTS)


def click_apply(page: Page, pause_ms: int) -> str:
    """
    Trigger the WTTJ Apply action.

    When the user is logged in, WTTJ's job-feed view removes the Apply button
    from the DOM entirely and instead relies on the keyboard shortcut "A".
    We therefore try the keyboard shortcut first, wait briefly for the modal,
    and only fall back to clicking a visible button if no modal appeared.
    """
    pause_s = max(pause_ms, 0) / 1000

    # --- Strategy 1: keyboard shortcut "A" (authenticated / feed view) ---
    try:
        page.keyboard.press("a")
        time.sleep(pause_s)
        # If the modal appeared, we're done.
        if detect_modal(page, timeout_ms=2000):
            return "keyboard:a"
    except Exception:
        pass

    # --- Strategy 2: explicit button click (unauthenticated / direct-link view) ---
    for selector in APPLY_BUTTON_SELECTORS:
        try:
            loc = page.locator(selector).first
            if loc.count() == 0:
                continue
            loc.scroll_into_view_if_needed(timeout=4000)
            loc.click(timeout=6000)
            time.sleep(pause_s)
            return selector
        except Exception:
            continue

    return ""


def detect_modal(page: Page, timeout_ms: int) -> bool:
    for selector in MODAL_OR_DRAWER_SELECTORS:
        try:
            page.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
            pass
    return False


def select_best(candidates: list[CandidateLink]) -> str:
    for c in candidates:
        if c.score > 0 and not is_wttj_url(c.url):
            return c.url
    return ""


class WTTJBrowserResolver:
    def __init__(
        self,
        user_data_dir: str = DEFAULT_WTTJ_PROFILE_DIR,
        headless: bool = False,
        pause_ms: int = 5000,
        debug_dir: str = DEFAULT_WTTJ_DEBUG_DIR,
        login_wait_s: int = DEFAULT_LOGIN_WAIT_TIMEOUT_S,
    ) -> None:
        if sync_playwright is None:
            raise RuntimeError("Install Playwright: pip install playwright && python -m playwright install chromium")
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.pause_ms = pause_ms
        self.debug_dir = debug_dir
        self.login_wait_s = login_wait_s
        self._pw = None
        self._ctx = None

    def __enter__(self) -> "WTTJBrowserResolver":
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(user_data_dir=self.user_data_dir, headless=self.headless, viewport={"width": 1440, "height": 1000})
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._ctx:
            self._ctx.close()
        if self._pw:
            self._pw.stop()

    def resolve(self, url: str, company: str = "", title: str = "", debug_prefix: str = "wttj_job") -> WTTJResolveResult:
        if not self._ctx:
            raise RuntimeError("Use WTTJBrowserResolver as a context manager")
        result = WTTJResolveResult(input_url=url, company=company, title=title)
        if is_wttj_email_control_url(url):
            result.error = "Refusing to open WTTJ email settings/unsubscribe URL."
            return result
        if not (is_wttj_job_detail_url(url) or is_sendgrid_tracking_url(url)):
            result.error = "Refusing to open URL that is neither a WTTJ /jobs/... page nor a SendGrid job-card tracking URL."
            return result
        page = self._ctx.new_page()
        debug_dir = Path(self.debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            result.page_url_before_click = page.url

            # When the input was a SendGrid tracking URL, record the clean WTTJ
            # /jobs/ page we landed on (path only, no tracking query params).
            if is_sendgrid_tracking_url(url) and is_wttj_job_detail_url(page.url):
                result.resolved_wttj_url = page.url.split("?")[0]

            # SendGrid should land on a real WTTJ job page before we click Apply.
            # If it lands on settings/unsubscribe or some non-job page, stop here.
            if is_wttj_email_control_url(page.url) or not is_wttj_job_detail_url(page.url):
                png = debug_dir / f"{debug_prefix}_bad_landing.png"
                html_path = debug_dir / f"{debug_prefix}_bad_landing.html"
                try:
                    page.screenshot(path=str(png), full_page=True)
                    html_path.write_text(page.content(), encoding="utf-8")
                    result.debug_screenshot_after = str(png)
                except Exception:
                    pass
                result.error = f"Navigation did not land on a WTTJ job page. Landed on: {page.url}"
                return result

            # Gate: skip jobs that WTTJ has marked as no longer available.
            # This check runs before login so we don't waste time authenticating
            # or clicking Apply on a dead listing.
            if detect_job_unavailable(page):
                result.job_unavailable = True
                result.error = "Job no longer available on WTTJ."
                return result

            # Gate: ensure the user is authenticated before clicking Apply.
            # Without login the Apply button either doesn't render or opens a
            # sign-in redirect instead of the external ATS modal.
            wait_for_login(page, self.login_wait_s)

            result.clicked_selector = click_apply(page, self.pause_ms)
            result.page_url_after_click = page.url
            # click_apply already confirmed the modal when using the keyboard
            # shortcut path; for the button-click path we check once more.
            if result.clicked_selector == "keyboard:a":
                result.modal_detected = True
            else:
                result.modal_detected = detect_modal(page, max(self.pause_ms, 1000))
            time.sleep(1)
            html = page.content()

            # Check for "Job no longer available" in the modal/page HTML.
            # This catches jobs that show the banner inside the WTTJ page after
            # the Apply button is clicked (e.g. Otta-hosted panels embedded on
            # the job detail page), without requiring a second page navigation.
            if detect_job_unavailable_in_html(html):
                result.job_unavailable = True
                result.error = "Job no longer available on WTTJ."
                png = debug_dir / f"{debug_prefix}_after.png"
                html_path = debug_dir / f"{debug_prefix}_after.html"
                try:
                    page.screenshot(path=str(png), full_page=True)
                    html_path.write_text(html, encoding="utf-8")
                    result.debug_screenshot_after = str(png)
                except Exception:
                    pass
                return result

            candidates = extract_candidates_from_html(html, company)
            result.candidates = [asdict(c) for c in candidates[:25]]
            result.selected_url = select_best(candidates)
            png = debug_dir / f"{debug_prefix}_after.png"
            html_path = debug_dir / f"{debug_prefix}_after.html"
            page.screenshot(path=str(png), full_page=True)
            html_path.write_text(html, encoding="utf-8")
            result.debug_screenshot_after = str(png)
            if not result.clicked_selector:
                result.error = "Could not click Apply"
            elif not result.selected_url:
                result.error = "Clicked Apply but no external apply URL was selected"
        except Exception as exc:
            result.error = str(exc)
        finally:
            page.close()
        return result


def save_resolver_results(results: list[WTTJResolveResult], output_json: str, output_jsonl: str) -> None:
    rows = [asdict(r) for r in results]
    write_json(output_json, rows, pretty=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

#!/usr/bin/env python3
"""Manual tester for the WTTJ Apply modal resolver.

Usage example:
    python inspect_wttj_apply_modal.py \\
        --url "https://app.welcometothejungle.com/jobs/E5BwXP4B" \\
        --company "Mechanize" \\
        --title "Junior Software Engineer" \\
        --keep-open
"""

from __future__ import annotations

import argparse
import time

from job_pipeline.constants import (
    DEFAULT_LOGIN_WAIT_TIMEOUT_S,
    DEFAULT_WTTJ_DEBUG_DIR,
    DEFAULT_WTTJ_PROFILE_DIR,
)
from job_pipeline.wttj_resolver import WTTJBrowserResolver, WTTJResolveResult


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Test the WTTJ Apply modal resolver against a single job URL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--url", required=True, help="WTTJ job URL to test")
    p.add_argument("--company", default="", help="Company name (improves URL scoring)")
    p.add_argument("--title", default="", help="Job title (for display only)")
    p.add_argument(
        "--pause-ms",
        type=int,
        default=5000,
        help="Milliseconds to wait after triggering Apply before reading the modal",
    )
    p.add_argument(
        "--login-wait-s",
        type=int,
        default=DEFAULT_LOGIN_WAIT_TIMEOUT_S,
        help="Seconds to wait for you to log in if not already authenticated",
    )
    p.add_argument(
        "--user-data-dir",
        default=DEFAULT_WTTJ_PROFILE_DIR,
        help="Playwright persistent profile directory (preserves login session)",
    )
    p.add_argument(
        "--debug-dir",
        default=DEFAULT_WTTJ_DEBUG_DIR,
        help="Directory where screenshot and HTML debug files are written",
    )
    p.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (login impossible in this mode)",
    )
    p.add_argument(
        "--keep-open",
        action="store_true",
        help="Keep the browser open after resolving (useful to inspect the modal)",
    )
    return p.parse_args()


def print_result(result: WTTJResolveResult) -> None:
    """Print a structured summary of the resolver result."""
    sep = "-" * 60
    print(sep)
    print(f"  input_url            : {result.input_url}")
    print(f"  job_unavailable      : {result.job_unavailable}")
    print(
        f"  page_url_before_click: {result.page_url_before_click or '(not navigated)'}"
    )
    print(
        f"  page_url_after_click : {result.page_url_after_click or '(not navigated)'}"
    )
    print(
        f"  clicked_selector     : {result.clicked_selector or '(none — Apply not triggered)'}"
    )
    print(f"  modal_detected       : {result.modal_detected}")
    print(f"  selected_url         : {result.selected_url or '(none)'}")
    if result.debug_screenshot_after:
        print(f"  debug_screenshot     : {result.debug_screenshot_after}")
    print(sep)

    if result.job_unavailable:
        print("[SKIP] Job is no longer available on WTTJ — listing was not processed.")
    elif result.error:
        print(f"[FAIL] {result.error}")
    elif result.selected_url:
        print(f"[OK]   External apply URL resolved: {result.selected_url}")
    elif result.modal_detected:
        print("[WARN] Modal opened but no external ATS URL was found inside it.")
    elif result.clicked_selector:
        print(
            "[WARN] Apply was triggered but modal did not appear — the page may have navigated instead."
        )
    else:
        print(
            "[FAIL] Apply could not be triggered (no button found and keyboard shortcut did not open a modal)."
        )

    if result.candidates:
        top = result.candidates[:5]
        print(f"\n  Top {len(top)} candidate URLs (by score):")
        for i, c in enumerate(top, 1):
            print(f"    {i}. score={c['score']:+d}  {c['url']}")
            if c.get("context"):
                print(f"         context: {c['context'][:120]}")


def main() -> None:
    args = parse_args()
    with WTTJBrowserResolver(
        user_data_dir=args.user_data_dir,
        headless=args.headless,
        pause_ms=args.pause_ms,
        debug_dir=args.debug_dir,
        login_wait_s=args.login_wait_s,
    ) as resolver:
        result = resolver.resolve(
            args.url,
            company=args.company,
            title=args.title,
            debug_prefix="manual_test",
        )
        print_result(result)

        if args.keep_open:
            print("\nKeeping browser open. Press Ctrl+C to quit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting.")


if __name__ == "__main__":
    main()

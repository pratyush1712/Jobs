from __future__ import annotations
import requests


def make_session() -> requests.Session:
    """Return a requests Session with realistic browser headers.

    Most ATS vendors (Greenhouse, Lever, Ashby, Workday, etc.) gate their
    responses behind User-Agent and Accept checks that reject simplistic
    bot-looking headers. Mirroring a real Chrome request passes most of
    those soft gates without requiring JavaScript execution.
    """
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        # Do NOT set Accept-Encoding manually. When requests/urllib3 owns this
        # header it also owns decompression. Overriding it (e.g. to include "br")
        # causes servers like Ashby to return brotli-encoded bytes that requests
        # cannot decode, giving the parser and LLM binary garbage instead of HTML.
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    })
    return s

"""
ANSI terminal color helpers.

All functions check ``sys.stdout.isatty()`` so that color codes are stripped
automatically when output is piped to a file or another program.
"""
from __future__ import annotations

import sys


def _tty() -> bool:
    return sys.stdout.isatty()


# Core formatter
def _fmt(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _tty() else text


# Styles
def bold(text: str) -> str:
    return _fmt("1", text)

def dim(text: str) -> str:
    return _fmt("2", text)

def italic(text: str) -> str:
    return _fmt("3", text)


# Standard colours
def red(text: str) -> str:
    return _fmt("31", text)

def green(text: str) -> str:
    return _fmt("32", text)

def yellow(text: str) -> str:
    return _fmt("33", text)

def blue(text: str) -> str:
    return _fmt("34", text)

def magenta(text: str) -> str:
    return _fmt("35", text)

def cyan(text: str) -> str:
    return _fmt("36", text)

def white(text: str) -> str:
    return _fmt("37", text)


# Bright variants
def bright_red(text: str) -> str:
    return _fmt("91", text)

def bright_green(text: str) -> str:
    return _fmt("92", text)

def bright_yellow(text: str) -> str:
    return _fmt("93", text)

def bright_cyan(text: str) -> str:
    return _fmt("96", text)

def bright_white(text: str) -> str:
    return _fmt("97", text)


# Semantic helpers used by the pipeline
def ok(text: str) -> str:
    """Successful enrichment."""
    return bright_green(text)

def warn(text: str) -> str:
    """Partial / low-confidence result."""
    return yellow(text)

def err(text: str) -> str:
    """Failed fetch or LLM error."""
    return bright_red(text)

def tag(text: str) -> str:
    """Supplementary tag like [pw]."""
    return cyan(text)

def counter(text: str) -> str:
    """Progress counter [n/total]."""
    return dim(text)

def label(text: str) -> str:
    """Company — Job title."""
    return bright_white(text)

def eta(text: str) -> str:
    """ETA / elapsed time annotation."""
    return dim(text)

def sep(text: str) -> str:
    """Separator / divider line."""
    return dim(text)

def header(text: str) -> str:
    """Section header."""
    return bold(bright_white(text))

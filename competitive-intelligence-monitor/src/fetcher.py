"""Fetch a URL and reduce it to clean, comparable text.

We strip scripts/styles/nav chrome and collapse whitespace so that small
cosmetic changes (a rotating CSS hash, a tracking pixel) don't register as
content changes. Only meaningful copy survives into the snapshot.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "CompetitiveIntelligenceMonitor/1.0 "
        "(+https://github.com/manthanjha7/manthanjha7)"
    )
}

# Tags that never carry product/pricing copy worth diffing.
_NOISE_TAGS = ["script", "style", "noscript", "svg", "nav", "footer", "header"]


def fetch_text(url: str, timeout: int = 20) -> str:
    """Return the visible, normalized text content of a page.

    Raises requests.HTTPError / requests.RequestException on network failure so
    the caller can record the source as "unreachable" rather than as changed.
    """
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    text = soup.get_text(separator="\n")
    return _normalize(text)


def _normalize(text: str) -> str:
    """Collapse blank lines and trailing whitespace for stable diffs."""
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)

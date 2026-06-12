"""Render analyses into a Markdown digest and (optionally) post to Slack."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import requests

DIGEST_DIR = Path(__file__).resolve().parent.parent / "digests"

_STARS = {1: "▁", 2: "▂", 3: "▄", 4: "▆", 5: "█"}


def _sig_badge(score: int) -> str:
    return f"{_STARS.get(score, '▁')} {score}/5"


def build_markdown(findings: list[dict], errors: list[dict]) -> str:
    """findings: list of {competitor, source, analysis}. errors: {competitor, source, error}."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Competitive Intelligence Digest", f"_{now}_", ""]

    if not findings:
        lines += ["No material changes detected across monitored sources.", ""]
    else:
        # Highest-significance findings first so the PM reads top-down.
        findings = sorted(
            findings, key=lambda f: f["analysis"].significance, reverse=True
        )
        lines.append(f"**{len(findings)} change(s) detected.**\n")
        for f in findings:
            a = f["analysis"]
            lines += [
                f"## {a.headline}",
                f"**{f['competitor']}** · {f['source']} · "
                f"`{a.category}` · {_sig_badge(a.significance)}",
                "",
                f"**What changed:** {a.what_changed}",
                "",
                f"**Why it matters for us:** {a.implication_for_us}",
                "",
                f"**Recommended action:** {a.recommended_action}",
                "",
                "---",
                "",
            ]

    if errors:
        lines += ["## Unreachable sources", ""]
        for e in errors:
            lines.append(f"- {e['competitor']} · {e['source']}: {e['error']}")
        lines.append("")

    return "\n".join(lines)


def save_markdown(markdown: str) -> Path:
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = DIGEST_DIR / f"digest-{stamp}.md"
    path.write_text(markdown)
    return path


def post_to_slack(webhook_url: str, findings: list[dict]) -> None:
    """Post a compact summary of the highest-significance findings to Slack."""
    if not webhook_url or not findings:
        return
    top = sorted(findings, key=lambda f: f["analysis"].significance, reverse=True)[:5]
    blocks = ["*Competitive Intelligence Digest*"]
    for f in top:
        a = f["analysis"]
        blocks.append(
            f"• *{f['competitor']}* ({a.significance}/5) — {a.headline}\n"
            f"   _{a.recommended_action}_"
        )
    requests.post(webhook_url, json={"text": "\n".join(blocks)}, timeout=15)

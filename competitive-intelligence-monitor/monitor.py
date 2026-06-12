#!/usr/bin/env python3
"""Competitive Intelligence Monitor — CLI entry point.

Fetches each competitor source listed in the config, detects content changes
against the last saved snapshot, asks Claude to interpret the *changed* ones in
the context of your product, and writes a Markdown digest (optionally posting a
summary to Slack).

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python monitor.py --config config.yaml
    python monitor.py --config config.yaml --dry-run   # fetch + diff, no Claude calls
"""

from __future__ import annotations

import argparse
import os
import sys

import anthropic
import requests
import yaml

from src import analyzer, digest, store
from src.fetcher import fetch_text


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run(config_path: str, dry_run: bool) -> int:
    config = load_config(config_path)
    model = config.get("model", "claude-opus-4-8")
    my_product = config.get("my_product", {})

    client = None
    if not dry_run:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
            return 1
        client = anthropic.Anthropic()

    findings: list[dict] = []
    errors: list[dict] = []
    committable: list[tuple[str, str, str, str]] = []

    for competitor in config.get("competitors", []):
        name = competitor["name"]
        for source in competitor.get("sources", []):
            label, url = source["label"], source["url"]
            stype = source.get("type", "homepage")
            print(f"→ {name} · {label} … ", end="", flush=True)

            try:
                text = fetch_text(url)
            except requests.RequestException as exc:
                print("unreachable")
                errors.append(
                    {"competitor": name, "source": label, "error": str(exc)}
                )
                continue

            result = store.detect_change(name, label, text)
            # Persist the new baseline regardless of analysis outcome.
            committable.append((name, label, url, text))

            if not result.changed:
                print("no change")
                continue

            if dry_run:
                print("CHANGED (dry-run, skipping analysis)")
                continue

            print("CHANGED — analyzing")
            analysis = analyzer.analyze(
                client, model, my_product, name, label, stype, result.diff
            )
            # Skip the noise the analyst itself flags as immaterial.
            if analysis.category == "no_material_change" and analysis.significance <= 1:
                continue
            findings.append(
                {"competitor": name, "source": label, "analysis": analysis}
            )

    # Only commit snapshots once the run has completed without crashing, so a
    # mid-run failure doesn't silently swallow an un-analyzed change next time.
    for name, label, url, text in committable:
        store.commit(name, label, url, text)

    markdown = digest.build_markdown(findings, errors)
    out_path = digest.save_markdown(markdown)
    print(f"\nDigest written to {out_path}")

    webhook = config.get("slack_webhook_url") or os.environ.get("SLACK_WEBHOOK_URL")
    if webhook and not dry_run:
        digest.post_to_slack(webhook, findings)
        print("Posted summary to Slack.")

    print(f"\n{'='*60}\n{markdown}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config YAML (default: config.yaml)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and diff sources but skip Claude analysis and Slack.",
    )
    args = parser.parse_args()
    return run(args.config, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

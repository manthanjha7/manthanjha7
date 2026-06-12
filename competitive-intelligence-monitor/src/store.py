"""Snapshot storage and change detection.

Each (competitor, source) pair gets one snapshot file under data/snapshots/.
On each run we compare the freshly fetched text against the stored snapshot;
if the content hash differs, the source is "changed" and a unified diff is
produced for Claude to interpret.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "snapshots"


@dataclass
class ChangeResult:
    changed: bool
    is_first_seen: bool
    old_text: str
    new_text: str
    diff: str


def _slug(competitor: str, label: str) -> str:
    raw = f"{competitor}::{label}".lower()
    digest = hashlib.sha1(raw.encode()).hexdigest()[:10]
    safe = "".join(c if c.isalnum() else "-" for c in raw)[:60]
    return f"{safe}-{digest}.json"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def detect_change(competitor: str, label: str, new_text: str) -> ChangeResult:
    """Compare new_text to the stored snapshot WITHOUT writing it back.

    Call commit() after a successful run to persist the new snapshot.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / _slug(competitor, label)

    if not path.exists():
        return ChangeResult(
            changed=True,
            is_first_seen=True,
            old_text="",
            new_text=new_text,
            diff="(first time this source has been seen)",
        )

    stored = json.loads(path.read_text())
    old_text = stored.get("text", "")

    if _content_hash(old_text) == _content_hash(new_text):
        return ChangeResult(False, False, old_text, new_text, "")

    diff = "\n".join(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
            n=2,
        )
    )
    return ChangeResult(True, False, old_text, new_text, diff)


def commit(competitor: str, label: str, url: str, new_text: str) -> None:
    """Persist the latest fetched text as the new baseline snapshot."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / _slug(competitor, label)
    path.write_text(
        json.dumps(
            {"competitor": competitor, "label": label, "url": url, "text": new_text},
            indent=2,
        )
    )

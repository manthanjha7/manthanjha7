# Competitive Intelligence Monitor

> Project #3 from *50 GitHub Project Ideas for Product Managers* — **Market analysis**.

An agent that watches your competitors' changelogs, pricing, and blog pages, detects when they actually change, and uses **Claude** to tell you *what* changed, *why it matters for your product*, and *what to do about it* — delivered as a Markdown digest and an optional Slack ping.

It does not just diff text. The same competitor change is a threat to one company and irrelevant to another, so every change is interpreted **through the lens of your product's positioning**, scored 1–5 for significance, and turned into a concrete recommended action.

## What it proves

Competitive analysis as a repeatable system instead of a once-a-quarter scramble: structured monitoring, signal-vs-noise judgment, and turning raw market movement into PM decisions.

## How it works

```
config.yaml ──► fetch pages ──► diff vs. last snapshot ──► Claude analysis ──► digest.md
   (your              (clean        (only changed             (scored +           + Slack
 watchlist)          text)          sources advance)          recommended)        summary
```

1. **Fetch** — each source URL is fetched and reduced to clean, comparable text (`src/fetcher.py`).
2. **Detect** — content is hashed and diffed against the last saved snapshot; unchanged sources are skipped, so you only pay for real movement (`src/store.py`).
3. **Analyze** — changed sources go to Claude with your product context. Structured outputs guarantee a valid, parseable result: headline, category, significance, implication, recommended action (`src/analyzer.py`).
4. **Report** — findings are sorted by significance into a Markdown digest, with an optional compact Slack summary of the top items (`src/digest.py`).

## Quick start

```bash
cd competitive-intelligence-monitor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml   # then edit your watchlist
export ANTHROPIC_API_KEY=sk-ant-...

# First run records baselines; later runs surface what changed.
python monitor.py --config config.yaml

# Fetch + diff only, no Claude calls (free, good for testing your config):
python monitor.py --config config.yaml --dry-run
```

The first run treats every source as "first seen" and records a baseline snapshot. Run it again after competitors ship something to see the analysis in action.

## Configuration

Edit `config.yaml` (see `config.example.yaml` for the full template):

- **`model`** — `claude-opus-4-8` for the sharpest analysis, or `claude-haiku-4-5` for cheap high-frequency runs.
- **`my_product`** — your name, one-liner, and differentiators. This is what makes the analysis specific to *you*.
- **`competitors`** — each with a list of `sources` (label, URL, and a `type` like `changelog` / `pricing` / `blog`).
- **`slack_webhook_url`** — optional; can also be set via the `SLACK_WEBHOOK_URL` env var.

## Run it on a schedule

A GitHub Actions workflow (`.github/workflows/monitor.yml`) runs the monitor every weekday morning. Add two repository secrets — `ANTHROPIC_API_KEY` and (optional) `SLACK_WEBHOOK_URL` — and it will post digests to Slack automatically. Snapshots are cached between runs so it remembers what it has already seen.

## Layout

```
competitive-intelligence-monitor/
├── monitor.py            # CLI entry point + orchestration
├── config.example.yaml   # copy to config.yaml
├── requirements.txt
├── src/
│   ├── fetcher.py        # fetch + clean page text
│   ├── store.py          # snapshots + change detection
│   ├── analyzer.py       # Claude analysis (structured output)
│   └── digest.py         # Markdown + Slack rendering
└── data/snapshots/       # saved baselines (gitignored)
```

## Notes

- `config.yaml`, snapshots, and digests are gitignored — your watchlist stays private.
- Respect each site's `robots.txt` and terms of service; this is built for public marketing/changelog pages and light, scheduled polling.

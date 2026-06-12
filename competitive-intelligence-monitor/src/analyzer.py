"""Turn a raw diff into structured competitive intelligence via Claude.

Given what changed on a competitor's page plus the context of YOUR product,
Claude classifies the change, scores how significant it is, and recommends a
concrete response. We use structured outputs so the result is always valid,
parseable JSON — no brittle prompt-shape parsing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

# Cap the diff we send so a large page rewrite doesn't blow up token cost.
_MAX_DIFF_CHARS = 6000

_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {
            "type": "string",
            "description": "One-line summary of what the competitor changed.",
        },
        "category": {
            "type": "string",
            "enum": [
                "new_feature",
                "pricing_change",
                "positioning_shift",
                "content_update",
                "no_material_change",
            ],
        },
        "significance": {
            "type": "integer",
            "description": "1 = noise, 5 = urgent strategic threat.",
        },
        "what_changed": {
            "type": "string",
            "description": "2-3 sentences on the substance of the change.",
        },
        "implication_for_us": {
            "type": "string",
            "description": "Why this does or does not matter for our product.",
        },
        "recommended_action": {
            "type": "string",
            "description": "One concrete next step for the PM, or 'No action needed'.",
        },
    },
    "required": [
        "headline",
        "category",
        "significance",
        "what_changed",
        "implication_for_us",
        "recommended_action",
    ],
    "additionalProperties": False,
}


@dataclass
class Analysis:
    headline: str
    category: str
    significance: int
    what_changed: str
    implication_for_us: str
    recommended_action: str


def _system_prompt(my_product: dict) -> str:
    diffs = "\n".join(f"- {d}" for d in my_product.get("differentiators", []))
    return (
        "You are a competitive intelligence analyst supporting a product manager.\n"
        "Judge every competitor change through the lens of OUR product below — "
        "the same change can be a threat to one company and irrelevant to another.\n\n"
        f"OUR PRODUCT: {my_product.get('name', 'our product')}\n"
        f"{my_product.get('one_liner', '')}\n"
        f"Our differentiators:\n{diffs}\n\n"
        "Be precise and unsentimental. If a change is cosmetic or a routine blog "
        "post, say so and score it low — do not manufacture urgency."
    )


def analyze(
    client: anthropic.Anthropic,
    model: str,
    my_product: dict,
    competitor: str,
    source_label: str,
    source_type: str,
    diff: str,
) -> Analysis:
    diff = diff[:_MAX_DIFF_CHARS]
    user_content = (
        f"Competitor: {competitor}\n"
        f"Source: {source_label} (type: {source_type})\n\n"
        f"Here is the diff between the previous and current version of the page "
        f"(unified diff format; lines starting with + were added, - were removed):\n\n"
        f"{diff}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=1200,
        system=_system_prompt(my_product),
        messages=[{"role": "user", "content": user_content}],
        output_config={
            "format": {"type": "json_schema", "schema": _ANALYSIS_SCHEMA}
        },
    )

    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return Analysis(**data)

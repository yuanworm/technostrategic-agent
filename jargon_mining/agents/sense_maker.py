"""
Sense-Maker agent — Lead A.

Takes a client brief (company, product, market, optional brief doc) and produces:
1. A thesis JSON with explicit client/targets split (schema below)
2. A jargon audit table for the CLIENT's own product/category

INVARIANT: The Sense-Maker PROPOSES a thesis with explicit uncertainty flags and
source provenance. A human must review the output before feeding it to collect.
"""

import json
from typing import Optional
from jargon_mining.agents.base import run_agent

_SENSE_MAKER_SYSTEM = """\
You are a sense-making agent. Your job is to research a company's product and market,
then produce TWO outputs:

OUTPUT 1: A structured thesis JSON (schema below)
OUTPUT 2: A jargon audit table for the client's own product/category

---
THESIS JSON SCHEMA — output this first, exactly as a JSON object:

{
  "client": {
    "company": "<company / seller name>",
    "vertical": "<which industry does the client/seller operate in>",
    "product": "<product name>",
    "product_category": "<how buyers in the target market actually categorise this>"
  },
  "targets": {
    "market": "<target market>",
    "bgm_roles": [
      {
        "title": "<role title, in local language if relevant>",
        "function": "<department/function>",
        "influence": "primary / secondary / gatekeeper"
      }
    ],
    "verticals": ["<target buyer vertical 1 — most important first>"],
    "culture": {
      "market": "<market name>",
      "key_norms": ["<decision-making norm 1>", "<norm 2>"],
      "language_notes": "<language / communication style notes>",
      "hierarchy_notes": "<how hierarchy affects buying decisions>"
    },
    "company_size": "<profile of target accounts>",
    "use_cases": ["<specific use case 1>"]
  },
  "competitors": ["<real competitor in this market — include local players>"],
  "thesis": "<2-3 sentences: who buys, why, what they care about — stated as a hypothesis>",
  "what_would_prove_this_wrong": [
    "<explicit falsification condition 1>",
    "<explicit falsification condition 2>"
  ],
  "lead_a_status": "GENERATED",
  "lead_a_sources": ["<publication name / URL>"],
  "lead_a_confidence": {
    "bgm_roles": "HIGH / MEDIUM / LOW",
    "competitor_frame": "HIGH / MEDIUM / LOW",
    "target_verticals": "HIGH / MEDIUM / LOW",
    "culture": "HIGH / MEDIUM / LOW",
    "thesis": "HIGH / MEDIUM / LOW"
  }
}

---
JARGON AUDIT TABLE — output this immediately after the JSON, under this exact heading:

## JARGON AUDIT — CLIENT PRODUCT CATEGORY

For 10–15 key technical concepts in the client's product/category, produce a table with
these exact columns:

| TECHNICAL CONCEPT | LAYMEN EXPLANATION | THE PROMISE | THE REALITY | SOURCE |
|---|---|---|---|---|

Rules:
- TECHNICAL CONCEPT: the jargon term as used in vendor/industry marketing
- LAYMEN EXPLANATION: what it actually means in plain language (one sentence)
- THE PROMISE: the formal/marketing claim vendors make about this concept (verbatim or close paraphrase)
- THE REALITY: what buyers/practitioners actually experience — from practitioner blogs, forums,
  analyst notes, or press coverage. Be specific. Cite numbers where available.
- SOURCE: publication name and year

Only include concepts where you found REAL evidence of the promise vs. reality gap. No invented examples.

---
Research guidelines:
- Use web_search extensively. Search for real evidence in the TARGET MARKET specifically.
- For bgm_roles: search actual job postings and org charts in the target market.
  Do not assume Western org structures apply.
- For competitors: include local/domestic players, not just global brands.
- For the jargon audit: search for practitioner complaints, analyst reality-checks, and
  post-mortems alongside vendor marketing claims.
- Confidence: HIGH = direct evidence found. MEDIUM = inferred from adjacent market.
  LOW = assumed.
"""


def run_sense_maker(
    company: str,
    product: str,
    market: str,
    model: str,
    brief_text: Optional[str] = None,
) -> tuple[dict, str]:
    """
    Run the Sense-Maker agent.

    Returns: (thesis_dict, jargon_audit_markdown)
    Raises ValueError if the JSON cannot be parsed.
    """
    brief_section = ""
    if brief_text:
        brief_section = f"\n\nCLIENT BRIEF (additional context):\n{brief_text}\n"

    user_message = (
        f"Client / seller: {company}\n"
        f"Product: {product}\n"
        f"Target market: {market}\n"
        f"{brief_section}\n"
        "Research thoroughly using web_search. Output the thesis JSON first, then the "
        "jargon audit table immediately after."
    )

    raw = run_agent(_SENSE_MAKER_SYSTEM, user_message, model)

    # Split on the jargon audit heading
    audit_heading = "## JARGON AUDIT"
    if audit_heading in raw:
        json_part = raw[:raw.index(audit_heading)]
        audit_part = raw[raw.index(audit_heading):]
    else:
        json_part = raw
        audit_part = ""

    # Extract outermost JSON object from the thesis part
    start = json_part.find("{")
    end = json_part.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            f"Sense-Maker output contains no JSON object.\nRaw output:\n{raw}"
        )
    cleaned = json_part[start : end + 1].strip()

    try:
        thesis = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Sense-Maker returned invalid JSON.\nError: {e}\nExtracted:\n{cleaned}"
        ) from e

    thesis.setdefault("lead_a_status", "GENERATED")
    thesis.setdefault("lead_a_sources", [])
    thesis.setdefault("lead_a_confidence", {})

    return thesis, audit_part

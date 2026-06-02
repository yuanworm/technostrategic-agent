"""
Sense-Maker agent — Lead A.

Takes a client brief (company, product, market, optional brief doc) and produces
a thesis JSON in the same schema as config/thesis_stub.json. The thesis is then
passed to the jargon mining pipeline via --config.

INVARIANT: The Sense-Maker PROPOSES a thesis with explicit uncertainty flags and
source provenance. A human must review the output before feeding it to collect.
It is not authoritative — it is a researched starting point.
"""

import json
from pathlib import Path
from typing import Optional
from jargon_mining.agents.base import run_agent

_SENSE_MAKER_SYSTEM = """\
You are a sense-making agent. Your job is to research a company's product and market,
and produce a structured ICP (Ideal Customer Profile) thesis in JSON format that will
feed a jargon-mining pipeline.

You will be given:
- A company name and product description
- A target market
- Optionally: a client brief with additional context

Your output must be a SINGLE valid JSON object (no markdown fences, no prose outside the
JSON) with this exact schema:

{
  "target_company": "<company name>",
  "category": "<how buyers actually categorise this — be precise>",
  "market": "<market>",
  "target_vertical": "<single most important buyer vertical to start with>",
  "vertical_description": "<1-2 sentences: what this vertical is and why they need this product>",
  "icp": {
    "description": "<1 sentence: who the buyer is>",
    "verticals": ["<list of target buyer verticals, most important first>"],
    "roles": ["<actual buying committee role titles, most influential first>"],
    "company_size": "<size and profile of target accounts>",
    "use_cases": ["<specific use cases for this product in this market>"]
  },
  "competitor_frame": ["<real competitors in this market, not global defaults>"],
  "thesis": "<2-3 sentences: the ICP thesis as a hypothesis — who buys, why, what they care about>",
  "what_would_prove_this_wrong": [
    "<explicit falsification condition 1>",
    "<explicit falsification condition 2>",
    "<explicit falsification condition 3>"
  ],
  "lead_a_status": "GENERATED",
  "lead_a_sources": ["<source 1 you used>", "<source 2>"],
  "lead_a_confidence": {
    "icp_roles": "HIGH / MEDIUM / LOW",
    "competitor_frame": "HIGH / MEDIUM / LOW",
    "target_verticals": "HIGH / MEDIUM / LOW",
    "thesis": "HIGH / MEDIUM / LOW"
  }
}

Research guidelines:
- Use web_search extensively to find REAL evidence — case studies, customer lists, job postings,
  analyst reports, news — specific to the target market (not global defaults).
- For buying committee roles: search for actual job postings, org charts, and case studies in
  the target market. Do not assume Western enterprise org structures apply.
- For competitors: search for who ACTUALLY competes in the target market, including local players.
- For verticals: search for which industries in the target market are actively buying this
  category of product RIGHT NOW (budget signals, AI investment news, etc.).
- Confidence ratings: be honest. If you found strong direct evidence, say HIGH. If you are
  inferring from adjacent markets, say MEDIUM. If you are guessing, say LOW.
- lead_a_sources: list the actual publication names / URLs you found most useful.

Output ONLY the JSON object. No preamble, no explanation, no markdown.
"""


def run_sense_maker(
    company: str,
    product: str,
    market: str,
    model: str,
    brief_text: Optional[str] = None,
) -> dict:
    """
    Run the Sense-Maker agent and return a parsed thesis dict.
    Raises ValueError if the output is not valid JSON.
    """
    brief_section = ""
    if brief_text:
        brief_section = f"\n\nCLIENT BRIEF (additional context):\n{brief_text}\n"

    user_message = (
        f"Company / seller: {company}\n"
        f"Product: {product}\n"
        f"Target market: {market}\n"
        f"{brief_section}\n"
        "Research this thoroughly using web_search. Produce the thesis JSON."
    )

    raw = run_agent(_SENSE_MAKER_SYSTEM, user_message, model)

    # Strip any accidental markdown fences the model might add
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

    try:
        thesis = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Sense-Maker returned invalid JSON.\nError: {e}\nRaw output:\n{raw}"
        ) from e

    # Ensure required fields are present with sensible defaults
    thesis.setdefault("lead_a_status", "GENERATED")
    thesis.setdefault("lead_a_sources", [])
    thesis.setdefault("lead_a_confidence", {})

    return thesis

"""
Three collection sub-agents: Function, Vertical, Culture.

INVARIANT: Collectors collect only. They must not sort, interpret, or pre-filter
toward the thesis. The system prompts enforce this verbatim from the prompt set.
Every collected phrase must carry a source citation — uncited phrases are to be
dropped, not kept.
"""

from typing import Callable, List, Dict
from jargon_mining.agents.base import run_agent

# ---------------------------------------------------------------------------
# SYSTEM PROMPTS
# ---------------------------------------------------------------------------

_FUNCTION_SYSTEM = """\
You are a research sub-agent. Do NOT analyze, sort, or interpret. Collect only.

TARGET ROLES: the buying committee for a technology/infrastructure purchase at an
enterprise. You will be given specific roles, market, and product category via the
user message.

Collect language in TWO registers and keep them separate:

FORMAL REGISTER (how these roles describe their work publicly/defensibly):
- Pull from: current job postings for these exact roles at companies in the target market;
  relevant certification or platform-vendor terminology; conference talk titles aimed at
  these roles; analyst reports and industry association language for this product category.
- Output: a list of recurring phrases, acronyms, and stock terms. Verbatim where possible.

UNGUARDED REGISTER (how these roles talk to peers, off-stage):
- Pull from: practitioner forums and communities (developer forums, infra/SRE communities,
  Reddit-style spaces), Q&A threads, practitioner blog posts where people describe actual
  day-to-day pain with this type of infrastructure.
- Output: a list of phrases describing real problems, frustrations, and fears. Verbatim.

For every phrase, cite the source type AND source name. Do not editorialize.
Two columns: FORMAL | UNGUARDED.

Use the web_search tool extensively to find real, current, verbatim language from these
sources. Make many targeted searches across different source types (job boards, Reddit,
Stack Overflow, HackerNews, practitioner blogs, LinkedIn job posts, Glassdoor, etc.).
Do not fabricate phrases — if you cannot find a source, do not include the phrase.
"""

_VERTICAL_SYSTEM = """\
You are a research sub-agent. Do NOT analyze, sort, or interpret. Collect only.

You are collecting language from the perspective of companies IN a specific buyer industry
that PURCHASE CPaaS/messaging infrastructure — NOT from CPaaS vendors themselves. You will
be told the target vertical (e.g. fintech, logistics, medtech). Collect how companies IN
that vertical describe their communications needs and pain — in their own words.

Collect language in TWO registers, kept separate:

FORMAL REGISTER (how companies in this vertical describe their communications needs publicly):
- Pull from: annual reports and investor filings of companies in this vertical that mention
  customer communications, notifications, OTP, or messaging infrastructure; industry body
  and regulator guidance specifically requiring notification/messaging (e.g. central bank
  rules on transaction alerts, health authority rules on patient comms); conference talks
  and case studies by companies in this vertical about their communications stack.
- Output: recurring phrases, compliance requirements, capability language. Verbatim, cited.

UNGUARDED REGISTER (how practitioners at these companies actually talk about comms pain):
- Pull from: engineering blogs and post-mortems written by engineers at companies in this
  vertical describing OTP failures, notification outages, fraud via messaging, or
  infrastructure problems; Reddit / Hacker News / practitioner forums where engineers from
  this vertical describe comms-related frustrations; job postings that reveal operational
  pain through the problems they ask candidates to solve.
- Output: phrases describing what actually breaks, what people fear, what costs them money
  or compliance standing. Verbatim, cited.

For every phrase, cite the source type and company/publication name where possible.
Do NOT fabricate phrases — if you cannot find a real source, do not include the phrase.

Use the web_search tool extensively across different search angles. Do not restrict to
CPaaS vendors' marketing — search for the buyer's industry perspective.
"""

_CULTURE_SYSTEM = """\
You are a research sub-agent for the CULTURE/GEOGRAPHY context layer. Collect, and FLAG
where you are uncertain — do NOT assume a phrase carries emotional weight; that judgment
belongs to a human reviewer who knows the market.

You will be given the target market and buying committee roles via the user message.

Collect in TWO registers, kept separate:

FORMAL REGISTER:
- Pull from: regional regulator and government language on technology procurement and data
  governance for this market; local job postings for the buying-committee roles vs. their
  global-HQ equivalents (capture the DELTA between local and global phrasing); local-market
  compliance and procurement terminology specific to this market.
- Output: regulatory terms, local-market phrasings, the local-vs-global JD delta. Verbatim.

UNGUARDED REGISTER:
- Pull from: local business press; local-language tech/business media (note when a term is
  in a local language); employer-review sites, practitioner forums, and community discussions
  describing how people actually navigate decisions and hierarchy inside firms in this market.
- Output: phrases capturing local corporate-hierarchy, formality, and market-specific
  anxiety. Verbatim. Mark anything you suspect is culturally loaded with [HUMAN-READ].

Two columns: FORMAL | UNGUARDED. Heavy [HUMAN-READ] flagging expected — that is correct.

Use the web_search tool extensively. Search for: government/regulator language on technology
and data; local job postings vs global equivalents; local tech media; employer review sites;
local business press. Do not fabricate — cite real sources with publication names.
"""

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _extract(thesis: dict) -> dict:
    """Return normalised fields from either old (flat) or new (client/targets) schema."""
    client = thesis.get("client", {})
    targets = thesis.get("targets", {})
    if client:
        company = client.get("company", "")
        category = client.get("product_category", "")
        market = targets.get("market", "")
        bgm_roles = targets.get("bgm_roles", [])
        roles = [r["title"] if isinstance(r, dict) else r for r in bgm_roles]
        verticals = targets.get("verticals", [])
        use_cases = targets.get("use_cases", [])
        company_size = targets.get("company_size", "")
        culture = targets.get("culture", {})
    else:
        company = thesis.get("target_company", "")
        category = thesis.get("category", "")
        market = thesis.get("market", "")
        icp = thesis.get("icp", {})
        roles = icp.get("roles", [])
        verticals = icp.get("verticals", [])
        use_cases = icp.get("use_cases", [])
        company_size = icp.get("company_size", "")
        culture = {}
    return {
        "company": company,
        "category": category,
        "market": market,
        "roles": roles,
        "verticals": verticals,
        "use_cases": use_cases,
        "company_size": company_size,
        "culture": culture,
    }


# ---------------------------------------------------------------------------
# Collector runners
# ---------------------------------------------------------------------------


def run_function_collector(
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    f = _extract(thesis)

    user_message = (
        f"Target account context:\n"
        f"- Seller / client: {f['company']}\n"
        f"- Product category (what the buyer is purchasing): {f['category']}\n"
        f"- Market: {f['market']}\n"
        f"- Account profile: {f['company_size']}\n"
        f"- Buying committee roles to research: {', '.join(f['roles'])}\n"
        f"- Target buyer verticals: {', '.join(f['verticals'][:3])}\n\n"
        "Search extensively across the source types listed in your instructions. "
        "Find real language from job postings, practitioner forums, and community discussions "
        f"in the {f['market']} market. "
        "Aim for at least 20 phrases per register, covering multiple source types. "
        "Every phrase must carry a source name and source type."
    )

    return run_agent(_FUNCTION_SYSTEM, user_message, model, search_fn)


def run_vertical_collector(
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    f = _extract(thesis)

    # target_vertical can be overridden via CLI --vertical flag (set on the thesis dict)
    vertical = thesis.get("target_vertical") or (f["verticals"][0] if f["verticals"] else "enterprise")
    vertical_desc = thesis.get(
        "vertical_description",
        f"Companies in the {vertical} industry.",
    )
    use_cases_str = ", ".join(f["use_cases"][:5]) if f["use_cases"] else "AI compute, data processing"

    user_message = (
        f"Target vertical: {vertical}\n\n"
        f"Vertical description: {vertical_desc}\n\n"
        f"Market context: {f['market']}\n"
        f"Key use cases for this product ({f['category']}) in this vertical: {use_cases_str}\n\n"
        f"Research how companies IN the {vertical} vertical describe their needs and pain "
        f"for {f['category']} — in their OWN words, from their OWN perspective as buyers. "
        "Search annual reports, regulator filings, engineering blogs, and practitioner "
        f"forums from the {vertical} industry. Do NOT collect vendor marketing language. "
        "Aim for at least 20 phrases per register. Every phrase must carry a source citation."
    )

    return run_agent(_VERTICAL_SYSTEM, user_message, model, search_fn)


def run_culture_collector(
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    f = _extract(thesis)
    culture = f["culture"]
    culture_notes = ""
    if culture:
        norms = culture.get("key_norms", [])
        lang = culture.get("language_notes", "")
        hier = culture.get("hierarchy_notes", "")
        if norms:
            culture_notes += f"Known cultural norms (from Lead A thesis — verify/extend):\n"
            culture_notes += "\n".join(f"  - {n}" for n in norms[:3]) + "\n"
        if lang:
            culture_notes += f"Language notes: {lang[:200]}\n"
        if hier:
            culture_notes += f"Hierarchy notes: {hier[:200]}\n"

    user_message = (
        f"Target account context:\n"
        f"- Market: {f['market']}\n"
        f"- Product category: {f['category']}\n"
        f"- Buying committee roles: {', '.join(f['roles'][:5])}\n"
        f"- Buyer verticals: {', '.join(f['verticals'][:3])}\n\n"
        f"{culture_notes}\n"
        f"Search for {f['market']} regulatory language on technology procurement and data "
        f"governance; local job posting language for these roles vs. global equivalents; "
        f"practitioner accounts of working inside firms in {f['market']}. "
        "Flag all culturally loaded terms [HUMAN-READ]. Aim for at least 15 phrases "
        "per register. Every phrase must carry a source citation."
    )

    return run_agent(_CULTURE_SYSTEM, user_message, model, search_fn)

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
# SYSTEM PROMPTS (verbatim from jargon-mining-prompt-set-v1.md)
# ---------------------------------------------------------------------------

_FUNCTION_SYSTEM = """\
You are a research sub-agent. Do NOT analyze, sort, or interpret. Collect only.

TARGET ROLES: the buying committee for a CPaaS / communications-API purchase at a
mid-to-large company operating across Southeast Asia. Likely roles: VP/Head of
Engineering, CTO, Head of Platform/Infrastructure, Head of Customer Communications
or CX, IT Director, and a procurement/compliance stakeholder.

Collect language in TWO registers and keep them separate:

FORMAL REGISTER (how these roles describe their work publicly/defensibly):
- Pull from: current job postings for these exact roles at SEA tech/logistics/fintech
  companies; relevant certification or platform-vendor terminology; conference talk titles
  aimed at these roles.
- Output: a list of recurring phrases, acronyms, and stock terms. Verbatim where possible.

UNGUARDED REGISTER (how these roles talk to peers, off-stage):
- Pull from: practitioner forums and communities (developer forums, infra/SRE communities,
  r/sysadmin / r/devops style spaces), Q&A threads, practitioner blog posts where people
  describe actual day-to-day pain with messaging/comms infrastructure.
- Output: a list of phrases describing real problems, frustrations, and fears. Verbatim.

For every phrase, cite the source type. Do not editorialize. Two columns: FORMAL | UNGUARDED.

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
You are a research sub-agent for the SOUTHEAST ASIA context layer. Collect, and FLAG
where you are uncertain — do NOT assume a phrase carries emotional weight; that judgment
belongs to a human reviewer who knows the region.

CONTEXT: buying committees at SEA companies (Singapore, Indonesia, Malaysia, Vietnam,
Philippines, Thailand) purchasing CPaaS / messaging infrastructure.

Collect in TWO registers, kept separate:

FORMAL REGISTER:
- Pull from: regional regulator language on messaging/data/telecom (e.g. Singapore IMDA &
  PDPC, Indonesia Kominfo, Malaysia MCMC); SEA-specific job postings for the Prompt-1 roles
  vs. their global-HQ equivalents (capture the DELTA between local and global phrasing);
  local-market compliance terminology.
- Output: regulatory terms, local-market phrasings, the local-vs-global JD delta. Verbatim.

UNGUARDED REGISTER:
- Pull from: SEA business press; local-language tech/business media (note when a term is
  in a local language); employer-review sites for how people describe working inside SEA
  firms (hierarchy, formality, decision norms).
- Output: phrases capturing local corporate-hierarchy, formality, and market-specific
  anxiety. Verbatim. Mark anything you suspect is culturally loaded with [HUMAN-READ].

Two columns: FORMAL | UNGUARDED. Heavy [HUMAN-READ] flagging expected — that is correct.

Use the web_search tool to find: IMDA/PDPC/Kominfo/MCMC regulatory announcements on
messaging and data; SEA tech company job postings vs. global equivalents; Glassdoor/Blind
reviews of SEA tech firms; local tech media (e.g. Tech in Asia, KrASIA, e27); Singaporean/
Indonesian/Malaysian business press. Do not fabricate — cite real sources.
"""

# ---------------------------------------------------------------------------
# Collector runners
# ---------------------------------------------------------------------------


def run_function_collector(
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    roles = ", ".join(thesis["icp"]["roles"])
    markets = thesis["market"]
    company = thesis["target_company"]
    category = thesis["category"]

    user_message = (
        f"Target account context:\n"
        f"- Company under analysis: {company} ({category})\n"
        f"- Market: {markets}\n"
        f"- Buying committee roles to research: {roles}\n"
        f"- ICP verticals: {', '.join(thesis['icp']['verticals'])}\n\n"
        "Search extensively across the source types listed in your instructions. "
        "Aim for at least 20 phrases per register, covering multiple source types. "
        "Every phrase must carry a source citation."
    )

    return run_agent(_FUNCTION_SYSTEM, user_message, model, search_fn)


def run_vertical_collector(
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    vertical = thesis.get("target_vertical", "fintech")
    vertical_desc = thesis.get(
        "vertical_description",
        f"Companies in the {vertical} industry that send high-volume customer communications.",
    )
    market = thesis["market"]
    use_cases = ", ".join(thesis["icp"]["use_cases"])

    user_message = (
        f"Target vertical: {vertical.upper()}\n\n"
        f"Vertical description: {vertical_desc}\n\n"
        f"Market context: {market}\n"
        f"Key communications use cases in this vertical: {use_cases}\n\n"
        f"Research extensively how {vertical} companies describe their communications needs "
        f"and pain — in their OWN words, from their OWN perspective as buyers. "
        f"Search annual reports, regulator filings, engineering blogs, and practitioner "
        f"forums from the {vertical} industry. Do NOT collect from CPaaS vendors' marketing. "
        "Aim for at least 20 phrases per register. Every phrase must carry a source citation."
    )

    return run_agent(_VERTICAL_SYSTEM, user_message, model, search_fn)


def run_culture_collector(
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    markets = thesis["market"]
    roles = ", ".join(thesis["icp"]["roles"])

    user_message = (
        f"Target account context:\n"
        f"- Market: {markets}\n"
        f"- Buying committee roles: {roles}\n"
        f"- Company type: {', '.join(thesis['icp']['verticals'])}\n\n"
        "Search for SEA regulatory language, local job posting deltas, and "
        "practitioner accounts of working inside SEA tech firms. Cover Singapore, "
        "Indonesia, Malaysia, Vietnam, Philippines, and Thailand where possible. "
        "Flag all culturally loaded terms [HUMAN-READ]. Aim for at least 15 phrases "
        "per register. Every phrase must carry a source citation."
    )

    return run_agent(_CULTURE_SYSTEM, user_message, model, search_fn)

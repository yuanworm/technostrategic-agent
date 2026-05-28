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

VERTICAL: CPaaS / communications-platform-as-a-service, and its immediate buyers
(companies sending high-volume customer communications — OTP, alerts, notifications —
across multiple SEA markets).

Collect language in TWO registers, kept separate:

FORMAL REGISTER (the industry's defensible, on-record language):
- Pull from: annual-report and 10-K RISK-FACTOR sections of public CPaaS companies
  (e.g. Twilio, Sinch, Bandwidth) AND of heavy CPaaS *buyers* (regional logistics, fintech,
  e-commerce); industry analyst report summaries (Gartner/IDC on CPaaS); regulatory filings
  touching messaging, data, telecom.
- Output: recurring risk language, category terms, compliance phrases. Verbatim.

UNGUARDED REGISTER (the visceral version):
- Pull from: trade press and practitioner blogs on CPaaS delivery problems, deliverability,
  carrier filtering, OTP failure, spam classification, multi-market routing pain.
- Output: phrases describing what actually goes wrong and what people fear. Verbatim.

For every phrase, cite source type. Two columns: FORMAL | UNGUARDED.

Use the web_search tool extensively. Search for CPaaS annual reports (Twilio 10-K, Sinch
annual report), Gartner CPaaS magic quadrant summaries, OTP delivery failure blog posts,
carrier filtering complaints, deliverability issues across SEA markets (Indonesia, Thailand,
Philippines, Vietnam, Malaysia, Singapore). Do not fabricate phrases — cite real sources.
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
    company = thesis["target_company"]
    category = thesis["category"]
    competitors = ", ".join(thesis["competitor_frame"][:4])

    user_message = (
        f"Target account context:\n"
        f"- Company under analysis: {company} ({category})\n"
        f"- Key CPaaS competitors for reference: {competitors}\n"
        f"- Market: {thesis['market']}\n"
        f"- Use cases: {', '.join(thesis['icp']['use_cases'])}\n\n"
        "Search for CPaaS industry language from the source types in your instructions. "
        "Prioritise annual report risk-factor language, analyst summaries, and "
        "practitioner accounts of real delivery failures. Aim for at least 20 phrases "
        "per register. Every phrase must carry a source citation."
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

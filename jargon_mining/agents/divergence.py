"""
Divergence-finder sub-agent — surfaces candidate "deleted realities" AND
a jargon audit table for the target verticals.

INVARIANT: The system surfaces ALL candidate divergences, explicitly including ones that
contradict Lead A's thesis, flagged [UNEXPECTED]. Never suppress or down-rank a finding
for disagreeing with the thesis. The system STOPS here — it does not pick the winner.
That is the human's call (Step 4 in the prompt set).
"""

from typing import Callable, List, Dict, Optional
from jargon_mining.agents.base import run_agent

_DIVERGENCE_SYSTEM = """\
You are a divergence-detection sub-agent. You will receive a classified phrase table.

Your job has TWO parts:

---
PART 1: DELETED REALITIES

Find pairs where the FORMAL register and the UNGUARDED register describe the SAME
underlying theme in OPPOSITE emotional tones. These divergences are CANDIDATE
"deleted realities" — places where the polished language has erased a pain the person
still feels.

CRITICAL: Surface ALL candidate divergences, including any that contradict the thesis.
Flag unexpected ones [UNEXPECTED]. Preserve [HUMAN-READ] flags from culture axis.
Do NOT select which deleted reality matters most — that is the human's call.

Format each entry as:

---
**THEME:** <one-line theme>
**FORMAL PHRASE:** "<phrase>"
**SOURCE:** <publication name / source type>
**UNGUARDED PHRASE:** "<phrase>"
**SOURCE:** <publication name / source type>
**THE DELETED REALITY (hypothesis):** <what does the formal phrase erase that the person still feels? State as hypothesis, not fact.>
*Flags: [UNEXPECTED] / [HUMAN-READ] if applicable, else "none"*

---

Rank entries by strength of tonal divergence, strongest first.

After all deleted reality entries, output this exact line:
## PIPELINE STOP — STEPS 4 AND 5 ARE HUMAN-ONLY

---
PART 2: JARGON AUDIT — TARGET VERTICALS

Immediately after the pipeline stop line, output a jargon audit table for the TARGET
VERTICALS represented in the collected phrases. This covers technical concepts the
BUYERS use to describe their own needs — not vendor marketing concepts.

Output under this exact heading:
## JARGON AUDIT — TARGET VERTICALS

For 10–15 key technical concepts found in the collected phrases, produce:

| TECHNICAL CONCEPT | LAYMEN EXPLANATION | THE PROMISE | THE REALITY | SOURCE |
|---|---|---|---|---|

Rules:
- TECHNICAL CONCEPT: jargon term as used by buyers or in buyer-industry context
- LAYMEN EXPLANATION: plain-language meaning (one sentence)
- THE PROMISE: the formal/aspirational framing (from the FORMAL register phrases)
- THE REALITY: the visceral/ground-truth version (from the UNGUARDED register phrases)
- SOURCE: publication name from the collected data

Only include concepts with clear evidence from the collected phrases. Do not invent examples.
"""


def run_divergence_finder(
    sorted_output: dict,
    thesis: dict,
    model: str,
    search_fn: Optional[Callable[[str, int], List[Dict]]] = None,
    collected_output: Optional[dict] = None,
) -> tuple[str, str]:
    """
    Run the divergence finder.

    Returns: (deleted_realities_markdown, jargon_audit_markdown)
    """
    sorted_table = sorted_output.get("raw_output", "")
    thesis_summary = thesis.get("thesis", "")
    what_wrong = thesis.get("what_would_prove_this_wrong", [])

    source_ref = ""
    if collected_output:
        parts = []
        for axis in ("function", "vertical", "culture"):
            raw = collected_output.get(axis, {}).get("raw_output", "")
            if raw:
                parts.append(f"=== SOURCE REFERENCE — {axis.upper()} AXIS ===\n{raw}")
        if parts:
            source_ref = (
                "\n\nOriginal collected phrases with citations (use for real source names):\n\n"
                + "\n\n".join(parts)
            )

    user_message = (
        "Below is the classified phrase table.\n\n"
        f"Lead A thesis (for [UNEXPECTED] calibration — do not filter toward it):\n"
        f"{thesis_summary}\n\n"
        "What would prove the thesis wrong:\n"
        + "\n".join(f"- {w}" for w in what_wrong)
        + "\n\n=== SORTED PHRASE TABLE ===\n"
        + sorted_table
        + source_ref
    )

    raw = run_agent(_DIVERGENCE_SYSTEM, user_message, model, search_fn)

    # Split on the jargon audit heading
    audit_heading = "## JARGON AUDIT — TARGET VERTICALS"
    if audit_heading in raw:
        deleted_realities = raw[:raw.index(audit_heading)].strip()
        jargon_audit = raw[raw.index(audit_heading):].strip()
    else:
        deleted_realities = raw
        jargon_audit = ""

    return deleted_realities, jargon_audit

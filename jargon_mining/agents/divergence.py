"""
Divergence-finder sub-agent — surfaces candidate "deleted realities."

INVARIANT: The system surfaces ALL candidate divergences, explicitly including ones that
contradict Lead A's thesis, flagged [UNEXPECTED]. Never suppress or down-rank a finding
for disagreeing with the thesis. The system STOPS here — it does not pick the winner.
That is the human's call (Step 4 in the prompt set).
"""

from typing import Callable, List, Dict, Optional
from jargon_mining.agents.base import run_agent

_DIVERGENCE_SYSTEM = """\
You are a divergence-detection sub-agent. You will receive the classified phrase table.

Your ONLY job: find pairs where the FORMAL register and the UNGUARDED register describe
the SAME underlying theme in OPPOSITE emotional tones. These divergences are CANDIDATE
"deleted realities" — places where the polished language has erased a pain the person
still feels.

For each candidate, output:
  THEME: (one line)
  FORMAL PHRASE: (the polished/defensible version) — SOURCE: (publication/source type, verbatim from the collected data)
  UNGUARDED PHRASE: (the visceral version) — SOURCE: (publication/source type, verbatim from the collected data)
  THE DELETED REALITY (hypothesis): what does the formal phrase erase that the person
    still feels? State as a HYPOTHESIS, not a fact.

CRITICAL: You are NOT selecting which deleted reality matters most. You surface ALL
candidate divergences, including any that contradict an expected thesis. If a strong
divergence appears that wasn't anticipated, flag it as [UNEXPECTED] — do not suppress it.
If a finding involves culturally loaded language flagged [HUMAN-READ], preserve that flag
in your output.

Output: ranked by strength of tonal divergence, strongest first.

Format each entry as:

---
**THEME:** <one-line theme>
**FORMAL PHRASE:** "<phrase>"
**SOURCE:** <publication name / source type from the collected data>
**UNGUARDED PHRASE:** "<phrase>"
**SOURCE:** <publication name / source type from the collected data>
**THE DELETED REALITY (hypothesis):** <hypothesis>
*Flags: [UNEXPECTED] / [HUMAN-READ] if applicable, else "none"*

---

After all entries, add a section:

## Pipeline stop
This document is the end of the automated pipeline. Steps 4 and 5 are human-only:
- Step 4: Cultural read + operative deleted-reality call (human judgment)
- Step 5: Write Pierce hypotheses from the chosen deleted reality

Do not add further analysis or recommendations.
"""


def run_divergence_finder(
    sorted_output: dict,
    thesis: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
    collected_output: Optional[dict] = None,
) -> str:
    sorted_table = sorted_output.get("raw_output", "")
    thesis_summary = thesis.get("thesis", "")
    what_wrong = thesis.get("what_would_prove_this_wrong", [])

    # Build a source-reference block from the original collected phrases so the
    # divergence finder can cite real publication names rather than generic axis labels.
    source_ref = ""
    if collected_output:
        parts = []
        for axis in ("function", "vertical", "culture"):
            raw = collected_output.get(axis, {}).get("raw_output", "")
            if raw:
                parts.append(f"=== SOURCE REFERENCE — {axis.upper()} AXIS ===\n{raw}")
        if parts:
            source_ref = (
                "\n\nThe following is the original collected data with source citations. "
                "Use it to find and include the real source name for each phrase you cite "
                "in your output — do not use generic labels like 'job posting' when the "
                "actual publication name is available.\n\n"
                + "\n\n".join(parts)
            )

    user_message = (
        "Below is the classified phrase table from the sort stage.\n\n"
        f"Lead A thesis (for [UNEXPECTED] calibration only — do not filter toward it):\n"
        f"{thesis_summary}\n\n"
        f"What would prove the thesis wrong (for [UNEXPECTED] calibration):\n"
        + "\n".join(f"- {w}" for w in what_wrong)
        + "\n\n"
        "=== SORTED PHRASE TABLE ===\n"
        f"{sorted_table}\n"
        f"{source_ref}"
    )

    return run_agent(_DIVERGENCE_SYSTEM, user_message, model, search_fn)

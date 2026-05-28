"""
Divergence-finder sub-agent — surfaces candidate "deleted realities."

INVARIANT: The system surfaces ALL candidate divergences, explicitly including ones that
contradict Lead A's thesis, flagged [UNEXPECTED]. Never suppress or down-rank a finding
for disagreeing with the thesis. The system STOPS here — it does not pick the winner.
That is the human's call (Step 4 in the prompt set).
"""

from typing import Callable, List, Dict
from jargon_mining.agents.base import run_agent

_DIVERGENCE_SYSTEM = """\
You are a divergence-detection sub-agent. You will receive the classified phrase table.

Your ONLY job: find pairs where the FORMAL register and the UNGUARDED register describe
the SAME underlying theme in OPPOSITE emotional tones. These divergences are CANDIDATE
"deleted realities" — places where the polished language has erased a pain the person
still feels.

For each candidate, output:
  THEME: (one line)
  FORMAL PHRASE: (the polished/defensible version)
  UNGUARDED PHRASE: (the visceral version)
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
**FORMAL PHRASE:** "<phrase>" *(source type)*
**UNGUARDED PHRASE:** "<phrase>" *(source type)*
**THE DELETED REALITY (hypothesis):** <hypothesis>
*Flags: [UNEXPECTED] / [HUMAN-READ] if applicable*

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
) -> str:
    sorted_table = sorted_output.get("raw_output", "")
    thesis_summary = thesis.get("thesis", "")
    what_wrong = thesis.get("what_would_prove_this_wrong", [])

    user_message = (
        "Below is the classified phrase table from the sort stage.\n\n"
        f"Lead A thesis (for [UNEXPECTED] calibration only — do not filter toward it):\n"
        f"{thesis_summary}\n\n"
        f"What would prove the thesis wrong (for [UNEXPECTED] calibration):\n"
        + "\n".join(f"- {w}" for w in what_wrong)
        + "\n\n"
        "=== SORTED PHRASE TABLE ===\n"
        f"{sorted_table}\n"
    )

    return run_agent(_DIVERGENCE_SYSTEM, user_message, model, search_fn)

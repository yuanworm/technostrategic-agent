"""
Sort sub-agent — classifies collected phrases as buyer-protective / seller-protective / ambiguous.

INVARIANT: Every sorted phrase carries one-line reasoning (WHO does it protect, from what).
No unexplained classifications. The sorter proposes — a human confirms.
"""

from typing import Callable, List, Dict
from jargon_mining.agents.base import run_agent

_SORT_SYSTEM = """\
You are a classification sub-agent. You will receive collected phrases from three axes
(function, vertical, culture), each in FORMAL and UNGUARDED registers.

For EACH phrase, classify it on ONE axis only:

  BUYER-PROTECTIVE  — language the buyer needs to defend the decision upward (to a board,
                      CFO, regulator). Structural. The kind of phrase you would SPEAK to
                      prove you belong in the room.
  SELLER-PROTECTIVE — language that lets the seller (or the buyer) AVOID naming the real
                      problem. Fluff. The kind of phrase you would PIERCE.

Rules:
- Give exactly ONE classification per phrase.
- Give ONE LINE of reasoning per phrase: WHO does this phrase protect, and from what?
- If a phrase could be either depending on context, mark it AMBIGUOUS and say why — do not
  force it. Ambiguous is a valid and useful answer.
- You are proposing, not deciding. A human confirms.

Output a table: PHRASE | AXIS | REGISTER | CLASSIFICATION | ONE-LINE REASON

The AXIS column should be one of: FUNCTION, VERTICAL, CULTURE.
The REGISTER column should be one of: FORMAL, UNGUARDED.
Do not add rows that weren't in the input. Do not drop rows.
Do not add commentary outside the table.
"""


def run_sorter(
    collected_output: dict,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    function_text = collected_output.get("function", {}).get("raw_output", "")
    vertical_text = collected_output.get("vertical", {}).get("raw_output", "")
    culture_text = collected_output.get("culture", {}).get("raw_output", "")

    user_message = (
        "Below are collected phrases from three axes. Classify each phrase per the "
        "instructions. Preserve ALL phrases — do not drop any.\n\n"
        "=== AXIS: FUNCTION (buying committee roles) ===\n"
        f"{function_text}\n\n"
        "=== AXIS: VERTICAL (CPaaS industry) ===\n"
        f"{vertical_text}\n\n"
        "=== AXIS: CULTURE (SEA geography) ===\n"
        f"{culture_text}\n"
    )

    return run_agent(_SORT_SYSTEM, user_message, model, search_fn)

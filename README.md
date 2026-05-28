# Jargon Mining Agent System

Mines an account's language across three axes — job function, industry vertical, geography/culture — finds where the **formal/defensible register diverges from the unguarded/visceral register**, and surfaces candidate "deleted realities": pains the polished language has erased but the buyer still feels. A human confirms the operative one and writes the Pierce hypotheses.

**v1 target:** 8x8 × CPaaS × SEA.

---

## Architecture

```
collect (3 collectors) → sort (1 sorter) → diverge (1 divergence finder) → [HUMAN STOPS HERE]
```

**Two leads:**
- **Lead A — Sense-Maker:** Forms the ICP/category/competitor thesis. *Stubbed in v1* — human-supplied via `config/thesis_stub.json`. TODO: build as an agent in v2.
- **Lead B — Orchestrator:** Fans out to collection sub-agents, runs sort, runs divergence detection. Implemented as the CLI.

**Sub-agents under B:**
- `FunctionCollector` — buying-committee roles, formal + unguarded language (Prompt 1)
- `VerticalCollector` — CPaaS industry language, formal + unguarded (Prompt 2)
- `CultureCollector` — SEA geography/culture, formal + unguarded + `[HUMAN-READ]` flags (Prompt 3)
- `Sorter` — classifies each phrase buyer-protective / seller-protective / ambiguous (Prompt 4)
- `DivergenceFinder` — surfaces formal↔unguarded tonal divergences as candidate deleted realities (Prompt 5)

---

## INVARIANTS

These are non-negotiable. Optimising them away silently breaks the system's purpose.

1. **Collectors collect only.** They must not sort, interpret, or pre-filter toward the thesis. Enforced structurally: separate agents, separate prompts, explicit instruction in each system prompt.

2. **B must be able to refute A.** The divergence finder surfaces *all* candidate deleted realities, explicitly including ones that contradict Lead A's thesis, flagged `[UNEXPECTED]`. Never suppressed or down-ranked for disagreeing with the thesis.

3. **The system never makes the final deleted-reality call.** Surfacing candidates = agent. Choosing the *operative* one = human. The pipeline stops at "ranked candidates + evidence" and hands off. No agent picks the winner.

4. **The cultural axis is human-gated.** The culture collector flags culturally loaded terms `[HUMAN-READ]` rather than asserting their weight. Culture-axis findings are presented *for human judgment*, never as resolved.

5. **Every phrase carries a source citation; every sorted phrase carries one-line reasoning.** No uncited phrases (hallucinated jargon poisons everything downstream). No unexplained classifications (un-inspectable black box). If a collector can't cite, the phrase is dropped.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and BRAVE_SEARCH_API_KEY
```

**Required env vars:**
- `ANTHROPIC_API_KEY` — your Anthropic API key
- `BRAVE_SEARCH_API_KEY` — Brave Search API key (get one at brave.com/search/api). Without this, collectors run but return no phrases.

---

## Running one stage at a time

The pipeline is **human-in-the-loop and sequential**. Run one stage, inspect the artifact, then proceed. Do not chain into an autonomous loop.

```bash
# Stage 1: Collect
python -m jargon_mining collect
# Inspect: outputs/01_collected.json
# Check: Are phrases verbatim? Do all have source citations?

# Stage 2: Sort
python -m jargon_mining sort
# Inspect: outputs/02_sorted.json
# Check: Every phrase classified? One-line reasoning present? AMBIGUOUS flagged?

# Stage 3: Diverge (pipeline stop)
python -m jargon_mining diverge
# Inspect: outputs/03_candidate_deleted_realities.md
# This is the human handoff point.
```

Or run all three with confirmation prompts between stages:

```bash
python -m jargon_mining run-all
```

**Options (all commands):**
```
--output-dir, -o    Artifact directory (default: outputs/)
--model, -m         Claude model (default: claude-opus-4-7)
--config, -c        Thesis config path (default: config/thesis_stub.json)
```

---

## Artifacts

| File | Stage | Contents |
|------|-------|----------|
| `outputs/01_collected.json` | collect | Raw output from all three collectors, with timestamps |
| `outputs/02_sorted.json` | sort | Markdown table: PHRASE \| AXIS \| REGISTER \| CLASSIFICATION \| ONE-LINE REASON |
| `outputs/03_candidate_deleted_realities.md` | diverge | Ranked divergences: THEME, FORMAL PHRASE, UNGUARDED PHRASE, DELETED REALITY hypothesis, flags |

---

## After the pipeline (human steps)

**Step 4 — Cultural read + operative deleted-reality call:**
1. Go through every `[HUMAN-READ]` flag in the divergence output. Decide which terms actually carry weight in the specific SEA market. This judgment belongs to a human who knows the region.
2. From the candidates, pick the one (or two) deleted realities that name a pain an 8x8-type buyer *feels* but the lexicon has erased. Not the most interesting — the most *operative*. Note any `[UNEXPECTED]` divergences seriously: if the system surfaced a deleted reality your thesis didn't predict, that is a signal to revise the thesis.

**Step 5 — Write the Pierce hypotheses:**

```
HANDSHAKE (their buyer-protective language) → PIERCE (the deleted reality, named).

Shape:
"You're running [their formal phrase] across six SEA markets —
 [pierce: e.g. 'does it flag you before a carrier in Indonesia silently
 drops your OTPs, or after revenue already moved?']"
```

These become Supra post material. ICP-filtered engagement → feeds back as labelled data to improve the sorter next cycle. That calibration log is the asset.

---

## Customising the thesis

Edit `config/thesis_stub.json` to change:
- `target_company`, `category`, `market` — the account triple
- `icp.roles` — buying committee roles to research
- `icp.verticals` — company types
- `competitor_frame` — reference competitors
- `thesis` — Lead A's hypothesis
- `what_would_prove_this_wrong` — explicit falsifiers (used by divergence finder to calibrate `[UNEXPECTED]` flags)

---

## TODO (v2)

- [ ] **Sense-Maker agent (Lead A):** Implement `python -m jargon_mining sense-make` using Prompt A from the prompt set, replacing the thesis stub. See `# TODO` in `jargon_mining/cli.py`.
- [ ] **Calibration loop:** Feed Step 5 Pierce hypothesis outcomes back as labelled data to refine the sorter.
- [ ] **Multi-account support:** Parameterise the triple fully; support batch runs across accounts.
- [ ] **Additional search backends:** Add Tavily, Exa, or other search APIs alongside Brave.

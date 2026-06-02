"""
Jargon Mining CLI — human-in-the-loop, one stage at a time.

Stages (run in order):
  sense-make → config/thesis_sensemade.json   (Lead A — researches ICP thesis)
  collect    → outputs/01_collected.json
  sort       → outputs/02_sorted.json
  diverge    → outputs/03_candidate_deleted_realities.md
  run-all    → all three collect→sort→diverge stages, with human confirmation
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()

from jargon_mining import config as cfg
from jargon_mining.search.backend import web_search
from jargon_mining.agents.collectors import (
    run_function_collector,
    run_vertical_collector,
    run_culture_collector,
)
from jargon_mining.agents.sorter import run_sorter
from jargon_mining.agents.divergence import run_divergence_finder
from jargon_mining.agents.sense_maker import run_sense_maker

console = Console()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"  [green]Wrote:[/green] {path}")


def _read_json(path: Path) -> dict:
    if not path.exists():
        console.print(f"[red]Missing required input:[/red] {path}")
        console.print("Run the previous stage first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def _write_text(path: Path, text: str) -> None:
    with open(path, "w") as f:
        f.write(text)
    console.print(f"  [green]Wrote:[/green] {path}")


def _shared_options(fn):
    fn = click.option(
        "--output-dir", "-o", default=None,
        help="Directory to write artifacts (default: outputs/)"
    )(fn)
    fn = click.option(
        "--model", "-m", default=None,
        help="Claude model to use (default: claude-opus-4-7)"
    )(fn)
    fn = click.option(
        "--config", "-c", default=None,
        help="Path to thesis config JSON (default: config/thesis_stub.json)"
    )(fn)
    fn = click.option(
        "--vertical", "-v", default=None,
        help="Override target_vertical from config (e.g. fintech, logistics, medtech)"
    )(fn)
    return fn


@click.group()
def cli():
    """Jargon Mining Agent System — collect → sort → diverge."""
    pass


# ---------------------------------------------------------------------------
# sense-make (Lead A)
# ---------------------------------------------------------------------------

@cli.command("sense-make")
@click.option("--company", "-C", required=True, help="Company / seller name (e.g. 'Singtel DICo')")
@click.option("--product", "-p", required=True, help="Product description (e.g. 'RE:AI (AI/GPUaaS)')")
@click.option("--market",  "-M", required=True, help="Target market (e.g. 'Japan')")
@click.option("--brief",   "-b", default=None,  help="Path to a brief doc (.md/.txt) for extra context")
@click.option("--output",  "-o", default=None,  help="Output path for thesis JSON (default: config/thesis_sensemade.json)")
@click.option("--model",   "-m", default=None,  help="Claude model to use")
def sense_make(company, product, market, brief, output, model):
    """
    Lead A: Research the ICP thesis for a given company/product/market.

    Reads an optional brief file, searches the web, and writes a thesis JSON
    that can be passed to `collect` via --config.

    INVARIANT: Output is a PROPOSED thesis — review it before running collect.
    The agent flags confidence levels per field and lists its sources.
    """
    model_ = cfg.get_model(model)
    out_path = Path(output) if output else Path("config/thesis_sensemade.json")

    brief_text = None
    if brief:
        brief_path = Path(brief)
        if not brief_path.exists():
            console.print(f"[red]Brief file not found:[/red] {brief_path}")
            sys.exit(1)
        brief_text = brief_path.read_text()

    console.print(Panel(
        f"[bold]Lead A: Sense-Make[/bold]\n"
        f"Company: {company}\n"
        f"Product: {product}\n"
        f"Market:  {market}\n"
        f"Brief:   {brief or '(none)'}\n"
        f"Model:   {model_}\n"
        f"Output:  {out_path}",
        title="Jargon Mining — Sense-Maker"
    ))

    console.print("\n[bold cyan]Running Sense-Maker agent...[/bold cyan]")
    console.print("  (searching for real buying committee, verticals, competitors)\n")

    thesis = run_sense_maker(company, product, market, model_, brief_text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(thesis, f, indent=2, ensure_ascii=False)
    console.print(f"  [green]Wrote:[/green] {out_path}")

    # Surface key findings for quick human review
    icp = thesis.get("icp", {})
    confidence = thesis.get("lead_a_confidence", {})
    console.print(Panel(
        f"[bold]Proposed thesis — REVIEW BEFORE RUNNING COLLECT[/bold]\n\n"
        f"Category:        {thesis.get('category', '?')}\n"
        f"Target vertical: {thesis.get('target_vertical', '?')}  "
        f"[confidence: {confidence.get('target_verticals', '?')}]\n"
        f"Roles:           {', '.join(icp.get('roles', [])[:3])} ...  "
        f"[confidence: {confidence.get('icp_roles', '?')}]\n"
        f"Competitors:     {', '.join(thesis.get('competitor_frame', [])[:3])} ...  "
        f"[confidence: {confidence.get('competitor_frame', '?')}]\n\n"
        f"Thesis:\n{thesis.get('thesis', '?')}\n\n"
        f"Sources used: {len(thesis.get('lead_a_sources', []))}\n\n"
        f"[bold yellow]Next:[/bold yellow] review {out_path}, then:\n"
        f"  python -m jargon_mining collect --config {out_path} --vertical <vertical>",
        title="Sense-Maker output"
    ))


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------

@cli.command()
@_shared_options
def collect(output_dir, model, config, vertical):
    """
    Stage 1: Run the three collection sub-agents (function, vertical, culture).

    Writes: outputs/01_collected.json

    INVARIANT: Collectors collect only. They do not sort, interpret, or filter.
    Every phrase in the output must carry a source citation.
    """
    thesis = cfg.load_thesis(config)
    if vertical:
        thesis["target_vertical"] = vertical
    out_dir = cfg.resolve_output_dir(output_dir)
    model_ = cfg.get_model(model)
    target = f"{thesis['target_company']} × {thesis['category']} × {thesis['market']}"

    console.print(Panel(
        f"[bold]Stage 1: Collect[/bold]\n"
        f"Target: {target}\n"
        f"Model: {model_}\n"
        f"Output: {out_dir / cfg.COLLECTED_FILE}",
        title="Jargon Mining"
    ))

    out_path = out_dir / cfg.COLLECTED_FILE

    # Resume support: if a prior run partially completed, pick up where it left off.
    if out_path.exists():
        result = _read_json(out_path)
        done = [k for k in ("function", "vertical", "culture") if k in result]
        if done:
            console.print(
                f"  [yellow]Resuming:[/yellow] found existing {out_path} "
                f"with {', '.join(done)} already done."
            )
    else:
        result = {}

    result.setdefault("metadata", {
        "target": target,
        "stage": "collect",
        "model": model_,
        "started_at": _now(),
        "lead_a_status": thesis.get("lead_a_status", "STUBBED"),
    })

    stages = [
        ("function", "Function Collector", run_function_collector),
        ("vertical", "Vertical Collector", run_vertical_collector),
        ("culture",  "Culture Collector",  run_culture_collector),
    ]

    for key, label, runner in stages:
        if key in result and result[key].get("raw_output"):
            console.print(f"\n[dim]Skipping {label} (already in {out_path.name}).[/dim]")
            continue
        console.print(f"\n[bold cyan]Running {label}...[/bold cyan]")
        output = runner(thesis, model_, web_search)
        result[key] = {"raw_output": output, "timestamp": _now()}
        # Write after each collector so partial progress is never lost.
        _write_json(out_path, result)
        console.print(f"  [green]{label} complete.[/green]")

    result["metadata"]["completed_at"] = _now()
    _write_json(out_path, result)

    console.print(Panel(
        f"[green]Stage 1 complete.[/green]\n"
        f"Inspect {out_path} before proceeding to `sort`.\n\n"
        "Check: Are phrases verbatim? Do all phrases have source citations?\n"
        "Check: Did the collectors collect without interpreting?",
        title="Inspection checkpoint"
    ))


# ---------------------------------------------------------------------------
# sort
# ---------------------------------------------------------------------------

@cli.command()
@_shared_options
def sort(output_dir, model, config, vertical):  # noqa: ARG001 (vertical unused in sort)
    """
    Stage 2: Classify collected phrases as buyer-protective / seller-protective / ambiguous.

    Reads:  outputs/01_collected.json
    Writes: outputs/02_sorted.json

    INVARIANT: Every phrase gets one-line reasoning. No uncategorised phrases.
    The sorter proposes — a human confirms.
    """
    thesis = cfg.load_thesis(config)
    out_dir = cfg.resolve_output_dir(output_dir)
    model_ = cfg.get_model(model)

    in_path = out_dir / cfg.COLLECTED_FILE
    out_path = out_dir / cfg.SORTED_FILE

    console.print(Panel(
        f"[bold]Stage 2: Sort[/bold]\n"
        f"Reading: {in_path}\n"
        f"Model: {model_}\n"
        f"Output: {out_path}",
        title="Jargon Mining"
    ))

    collected = _read_json(in_path)

    console.print("\n[bold cyan]Running Sort sub-agent...[/bold cyan]")
    sorted_output = run_sorter(collected, model_, web_search)

    result = {
        "metadata": {
            "stage": "sort",
            "model": model_,
            "source": str(in_path),
            "timestamp": _now(),
        },
        "raw_output": sorted_output,
    }

    _write_json(out_path, result)

    console.print(Panel(
        f"[green]Stage 2 complete.[/green]\n"
        f"Inspect {out_path} before proceeding to `diverge`.\n\n"
        "Check: Does every phrase have a classification?\n"
        "Check: Does every classification have one-line reasoning?\n"
        "Check: Are AMBIGUOUS calls flagged (not forced)?",
        title="Inspection checkpoint"
    ))


# ---------------------------------------------------------------------------
# diverge
# ---------------------------------------------------------------------------

@cli.command()
@_shared_options
def diverge(output_dir, model, config, vertical):  # noqa: ARG001 (vertical unused in diverge)
    """
    Stage 3: Find formal↔unguarded divergences — candidate deleted realities.

    Reads:  outputs/02_sorted.json
    Writes: outputs/03_candidate_deleted_realities.md

    INVARIANT: ALL candidate divergences are surfaced, including [UNEXPECTED] ones
    that contradict Lead A's thesis. The system stops here — it does not pick the winner.
    Step 4 and Step 5 are human-only.
    """
    thesis = cfg.load_thesis(config)
    out_dir = cfg.resolve_output_dir(output_dir)
    model_ = cfg.get_model(model)

    in_path = out_dir / cfg.SORTED_FILE
    out_path = out_dir / cfg.DIVERGENCE_FILE

    console.print(Panel(
        f"[bold]Stage 3: Diverge[/bold]\n"
        f"Reading: {in_path}\n"
        f"Model: {model_}\n"
        f"Output: {out_path}",
        title="Jargon Mining"
    ))

    sorted_data = _read_json(in_path)

    # Pass collected phrases so divergence finder can surface real source citations.
    collected_path = out_dir / cfg.COLLECTED_FILE
    collected_data = _read_json(collected_path) if collected_path.exists() else None

    console.print("\n[bold cyan]Running Divergence Finder...[/bold cyan]")
    divergence_md = run_divergence_finder(sorted_data, thesis, model_, web_search, collected_data)

    header = (
        f"# Candidate Deleted Realities\n\n"
        f"**Target:** {thesis['target_company']} × {thesis['category']} × {thesis['market']}  \n"
        f"**Generated:** {_now()}  \n"
        f"**Lead A status:** {thesis.get('lead_a_status', 'STUBBED')}  \n\n"
        "---\n\n"
        "> **Pipeline stop.** This document is the end of the automated pipeline.  \n"
        "> **Step 4** (human): cultural read + operative deleted-reality call.  \n"
        "> **Step 5** (human): write Pierce hypotheses from the chosen deleted reality.  \n\n"
        "---\n\n"
    )

    _write_text(out_path, header + divergence_md)

    console.print(Panel(
        f"[green]Stage 3 complete. Pipeline stop.[/green]\n\n"
        f"The candidate deleted realities are in:\n{out_path}\n\n"
        "[bold]Step 4 is yours (human):[/bold]\n"
        "1. Go through every [HUMAN-READ] flag (culture axis) and decide which terms\n"
        "   actually carry weight in the specific SEA market.\n"
        "2. From the candidates, pick the operative deleted reality — the one a buyer\n"
        "   feels but the lexicon has erased. Note any [UNEXPECTED] divergences seriously.\n\n"
        "[bold]Step 5 is yours (human):[/bold]\n"
        "Turn the chosen deleted reality into 2–3 testable Pierce lines:\n"
        '  "You\'re running [formal phrase] — [pierce: the deleted reality named]?"',
        title="Human handoff"
    ))


# ---------------------------------------------------------------------------
# run-all
# ---------------------------------------------------------------------------

@cli.command("run-all")
@_shared_options
def run_all(output_dir, model, config, vertical):
    """
    Run all three stages sequentially with human confirmation between each.

    collect → [inspect] → sort → [inspect] → diverge
    """
    thesis = cfg.load_thesis(config)
    out_dir = cfg.resolve_output_dir(output_dir)
    target = f"{thesis['target_company']} × {thesis['category']} × {thesis['market']}"

    console.print(Panel(
        f"[bold]Full pipeline: collect → sort → diverge[/bold]\n"
        f"Target: {target}\n"
        "Manual inspection checkpoints between each stage.",
        title="Jargon Mining — Run All"
    ))

    ctx = click.get_current_context()

    ctx.invoke(collect, output_dir=output_dir, model=model, config=config, vertical=vertical)

    console.print("\n")
    if not click.confirm(
        f"Inspect {out_dir / cfg.COLLECTED_FILE}. Proceed to sort?",
        default=True
    ):
        console.print("Stopped after collect. Run `sort` manually when ready.")
        return

    ctx.invoke(sort, output_dir=output_dir, model=model, config=config, vertical=vertical)

    console.print("\n")
    if not click.confirm(
        f"Inspect {out_dir / cfg.SORTED_FILE}. Proceed to diverge?",
        default=True
    ):
        console.print("Stopped after sort. Run `diverge` manually when ready.")
        return

    ctx.invoke(diverge, output_dir=output_dir, model=model, config=config, vertical=vertical)

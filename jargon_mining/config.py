import json
import os
from pathlib import Path


_DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "thesis_stub.json"
_DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
_DEFAULT_MODEL = "claude-opus-4-7"

COLLECTED_FILE = "01_collected.json"
SORTED_FILE = "02_sorted.json"
DIVERGENCE_FILE = "03_candidate_deleted_realities.md"
JARGON_AUDIT_TARGETS_FILE = "04_jargon_audit_targets.md"


def load_thesis(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path else _DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(f"Thesis config not found: {path}")
    with open(path) as f:
        return json.load(f)


def resolve_output_dir(output_dir: str | None = None) -> Path:
    d = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_model(model: str | None = None) -> str:
    return model or os.getenv("JARGON_MINING_MODEL", _DEFAULT_MODEL)

"""Load YAML configuration from `configs/` and resolve repository-relative paths."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "configs"


def load_config(name: str) -> dict:
    """Return the parsed contents of `configs/<name>.yaml`."""
    with open(CONFIG_DIR / f"{name}.yaml") as fh:
        return yaml.safe_load(fh)


def repo_path(relative: str | Path) -> Path:
    """Resolve a path from config (relative to the repository root) to an absolute path."""
    return REPO_ROOT / relative

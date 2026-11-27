"""Load YAML configuration from `configs/` and resolve repository-relative paths."""

from pathlib import Path

import yaml

__all__ = ["load_config", "repo_path"]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = _REPO_ROOT / "configs"


def load_config(name: str) -> dict:
    """Return the parsed contents of `configs/<name>.yaml`."""
    with (_CONFIG_DIR / f"{name}.yaml").open() as fh:
        config: dict = yaml.safe_load(fh)
    return config


def repo_path(relative: str | Path) -> Path:
    """Resolve a path from config (relative to the repository root) to an absolute path."""
    return _REPO_ROOT / relative

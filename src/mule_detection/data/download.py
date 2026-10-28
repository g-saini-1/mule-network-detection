"""Download the configured dataset files from Kaggle and record their hashes.

Credentials are read by the Kaggle client from outside the repository (e.g.
`~/.kaggle/access_token`). Each downloaded file is recorded in a JSON manifest with its
SHA-256 hash, size and Kaggle creation date, so a later run can confirm the local copy is
unchanged and skip the download.

Run with `python -m mule_detection.data.download [--force]`.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mule_detection.utils.config import load_config, repo_path

CHUNK_BYTES = 1 << 20


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(path: Path) -> dict:
    """Return the manifest at `path`, or an empty one if it doesn't exist yet."""
    if not path.exists():
        return {}
    manifest: dict = json.loads(path.read_text())
    return manifest


def is_current(target: Path, entry: dict | None) -> bool:
    """True if `target` exists and its hash matches the manifest entry."""
    return target.exists() and entry is not None and entry.get("sha256") == sha256(target)


def _authenticated_api() -> Any:
    # The Kaggle client is untyped, so it is passed around as `Any`.
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    return api


def download_dataset(config: dict | None = None, force: bool = False, api: Any = None) -> dict:
    """Download each configured file unless an unchanged copy is already present.

    Returns the updated manifest. `api` can be injected for testing; by default an
    authenticated Kaggle client is created.
    """
    config = config or load_config("data")
    slug = config["kaggle_dataset"]
    raw_dir = repo_path(config["paths"]["raw"])
    manifest_path = repo_path(config["paths"]["manifest"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    api = api or _authenticated_api()
    remote = {f.name: f for f in api.dataset_list_files(slug).files}
    manifest = read_manifest(manifest_path)

    for file_name in config["files"].values():
        if file_name not in remote:
            raise FileNotFoundError(f"{file_name} is not listed in Kaggle dataset {slug}")
        target = raw_dir / file_name

        if not force and is_current(target, manifest.get(file_name)):
            print(f"{file_name}: present and unchanged, skipping")
            continue

        print(f"{file_name}: downloading")
        api.dataset_download_file(
            slug, file_name, path=raw_dir, force=True, quiet=False, unzip=True
        )
        manifest[file_name] = {
            "sha256": sha256(target),
            "bytes": target.stat().st_size,
            "kaggle_dataset": slug,
            "kaggle_creation_date": str(remote[file_name].creation_date),
            "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    return manifest


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download even if unchanged")
    args = parser.parse_args()
    download_dataset(force=args.force)


if __name__ == "__main__":
    main()

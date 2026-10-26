"""Tests for the download script's hashing and skip logic, with Kaggle replaced by a fake."""

from types import SimpleNamespace

import pytest

from mule_detection.data.download import download_dataset, read_manifest, sha256

SLUG = "owner/dataset"


class FakeKaggle:
    """Stands in for the Kaggle client: lists files and 'downloads' fixed content."""

    def __init__(self, contents: dict[str, bytes]):
        self.contents = contents
        self.downloads: list[str] = []

    def dataset_list_files(self, slug):
        files = [SimpleNamespace(name=n, creation_date="2025-07-08") for n in self.contents]
        return SimpleNamespace(files=files)

    def dataset_download_file(self, slug, file_name, path, **kwargs):
        (path / file_name).write_bytes(self.contents[file_name])
        self.downloads.append(file_name)


def make_config(tmp_path, files):
    return {
        "kaggle_dataset": SLUG,
        "files": files,
        "paths": {"raw": str(tmp_path / "raw"), "manifest": str(tmp_path / "raw/manifest.json")},
    }


def test_sha256_matches_known_digest(tmp_path):
    path = tmp_path / "f.txt"
    path.write_bytes(b"abc")
    assert sha256(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_first_run_downloads_and_records_manifest(tmp_path):
    api = FakeKaggle({"a.csv": b"1,2\n"})
    manifest = download_dataset(make_config(tmp_path, {"t": "a.csv"}), api=api)
    assert api.downloads == ["a.csv"]
    assert manifest["a.csv"]["sha256"] == sha256(tmp_path / "raw/a.csv")
    assert manifest["a.csv"]["bytes"] == 4
    assert read_manifest(tmp_path / "raw/manifest.json") == manifest


def test_second_run_skips_unchanged_file(tmp_path):
    config = make_config(tmp_path, {"t": "a.csv"})
    api = FakeKaggle({"a.csv": b"1,2\n"})
    download_dataset(config, api=api)
    download_dataset(config, api=api)
    assert api.downloads == ["a.csv"]


def test_changed_local_file_is_downloaded_again(tmp_path):
    config = make_config(tmp_path, {"t": "a.csv"})
    api = FakeKaggle({"a.csv": b"1,2\n"})
    download_dataset(config, api=api)
    (tmp_path / "raw/a.csv").write_bytes(b"corrupted")
    download_dataset(config, api=api)
    assert api.downloads == ["a.csv", "a.csv"]
    assert (tmp_path / "raw/a.csv").read_bytes() == b"1,2\n"


def test_force_downloads_even_if_unchanged(tmp_path):
    config = make_config(tmp_path, {"t": "a.csv"})
    api = FakeKaggle({"a.csv": b"1,2\n"})
    download_dataset(config, api=api)
    download_dataset(config, force=True, api=api)
    assert api.downloads == ["a.csv", "a.csv"]


def test_file_not_in_dataset_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        download_dataset(make_config(tmp_path, {"t": "missing.csv"}), api=FakeKaggle({}))

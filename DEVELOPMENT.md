# Development standards

How code in this repository is written, checked and tested. Tooling choices and their
reasoning are in `docs/decisions.md` (2026-10-28, "Adopt automated code-quality checks").

Standards marked **enforced** are checked automatically by `make check`, pre-commit and CI.
Standards marked **from Stage N** apply to new code from that stage onwards.

## Checks and tooling

| Check | Tool | Runs in |
|---|---|---|
| Formatting | `ruff format` (line length 100) | pre-commit, `make check`, CI |
| Lint | `ruff check` with the rule set in `pyproject.toml` | pre-commit, `make check`, CI |
| Types | `mypy` on `src/` | `make check`, CI |
| Tests | `pytest` | `make check`, CI (without `data` tests) |
| Notebook outputs stripped | `nbstripout` | pre-commit |
| Large files, private keys, YAML/TOML syntax | `pre-commit-hooks` | pre-commit |

Table 1. Automated checks.

- **`make check` is the definition of done** for any code change. CI runs the same target on
  every push to `main` and every pull request.
- **Tool versions come from `uv.lock`.** Pre-commit runs ruff and nbstripout through `uv run`, so
  the editor, the hooks and CI all use the same versions.
- **Python 3.12 only.**

## Code

- **Enforced: type annotations on every function in `src/`.** Tests are exempt. An explicit
  `Any` is used only where a third-party library is untyped (e.g. the Kaggle client).
- **Enforced: Google-style docstrings** on every public module, class and function in `src/`.
  Docstrings cite rule numbers (e.g. R4) rather than restating reasoning.
- **Enforced: `pathlib` for file paths**, not `os.path` or bare `open()`.
- **Configuration, not constants.** Paths, dates, thresholds, costs and seeds live in
  `configs/*.yaml`, read with `mule_detection.utils.config.load_config()`.
- **From Stage 2: pure feature and rule functions.** Each takes a DataFrame and an `as_at`
  timestamp and returns a DataFrame or Series, with no file reads, config reads or global state
  inside. File and config access happens only in entry points (`main()` and `make` targets).
- **From Stage 2: logging, not `print`, in pipeline code.** One logger per module
  (`logging.getLogger(__name__)`); `print` stays only for deliberate command-line summaries.

## Tests

- **Layout:** `tests/test_<module>.py`, one file per module.
- **Naming:** a test that checks a numbered rule starts with that rule, e.g.
  `test_r4_order_of_receipt_and_send_does_not_matter`.
- **Small, hand-built frames.** Unit tests build the few rows they need; they never read
  `data/raw`.
- **Enforced: registered markers only.** A test that needs the downloaded dataset is marked
  `@pytest.mark.data`; CI skips these.
- **From Stage 2: a leakage test for every time-based feature**, and property-based tests
  (`hypothesis`) for the general rule that adding payments at or after `as_at` never changes a
  feature value.
- **From Stage 2: coverage measured** with `pytest-cov` on `src/`. A minimum is set from the first
  measured figure, not chosen in advance.

## Data

- **From Stage 2: schemas at stage boundaries.** Frames passed between stages (transactions,
  labels, features, scores) are checked against a `pandera` schema: column names, dtypes,
  nullability and value ranges.
- **Sort before time-based computation.** The transactions file is not in time order.

## Reproducibility

- **From Stage 3: a run manifest for every reported number.** Each run that produces figures for a
  report writes a JSON file beside its output with the git commit, a hash of the config, the data
  file hashes, the random seed and the run time.
- **From Stage 3: seeds from config.** Every random operation takes its seed from
  `configs/*.yaml`.
- **Notebooks stay thin.** They import from `mule_detection`, and explore or display results;
  logic used more than once moves into `src/`.

## Before a pull request

1. `make check` passes.
2. If code that produces data or reported figures changed (`src/mule_detection/data/` now;
   `rules/`, `features/` and `models/` later), the affected `make` targets are re-run on the real
   data, the `data` tests are run locally (`uv run pytest -m data`), and the headline figures
   still match the document that owns them.
3. If a notebook is affected, it runs from top to bottom.
4. If documentation changed, the documentation checks in `.claude/skills/docs-check/SKILL.md`
   pass.
5. Any departure from `scope_and_rationale.md` has a `docs/decisions.md` entry.
6. No data, credentials, notebook outputs, personal email addresses or local paths are committed.

The pull request description states what changed, why, and how it was verified, with the
commands run and the figures they produced.

## Not used

Docker, experiment-tracking servers (e.g. MLflow), data version control (e.g. DVC) and fixed
100% coverage targets. Each adds upkeep without improving trust in a single-author, one-dataset
project; the run manifest covers the reproducibility they would add.

# Development standards

How code in this repository is written, checked and tested. Tooling choices and their
reasoning are in `docs/decisions.md` (2026-10-28, "Adopt automated code-quality checks").

Standards marked **enforced** are checked automatically by `make check`, pre-commit and CI.

## Checks and tooling

| Check | Tool |
|---|---|
| Formatting | `ruff format` (line length 100) |
| Lint | `ruff check` with the rule set in `pyproject.toml` |
| Types | `mypy` on `src/` |
| Tests | `pytest` |
| Notebook outputs stripped | `nbstripout` |
| Large files, private keys, YAML/TOML syntax | `pre-commit-hooks` |

Table 1. Automated checks and their tools. Where each runs is set out in
[docs/test_strategy.md](docs/test_strategy.md) ("Quality gates").

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
- **Public and private names.** Every module in `src/` that defines names declares `__all__`,
  listing the module's interface: names other code uses or is designed to use, and names that
  describe the shape of a public function's output. Any other module-level name starts with `_`,
  apart from the module's `logger`. Tests may import a private name to test it directly.
- **Configuration, not constants.** Paths, dates, thresholds, costs and seeds live in
  `configs/*.yaml`, read with `mule_detection.utils.config.load_config()`.
- **Pure rule and feature functions.** Each takes DataFrames and returns a DataFrame or Series,
  with no file reads, config reads or global state inside. File and config access happens only
  in entry points (`main()` and `make` targets). Detection rules and features also take an
  `as_at` timestamp and use only transactions before it.
- **Logging, not `print`, in pipeline code.** One logger per module
  (`logging.getLogger(__name__)`); `print` stays only for deliberate command-line summaries.

## Tests

The testing approach (test levels, test types, test data and quality gates) is in
[docs/test_strategy.md](docs/test_strategy.md); the conventions for writing tests are below.

- **Layout:** `tests/test_<module>.py`, one file per module.
- **Test behaviour, not implementation.** Each test checks one behaviour, e.g. one condition of
  a rule, through arrange, act and assert steps.
- **Naming:** the name states the behaviour and its expected result, not the input, and starts
  with the rule it checks, e.g. `test_p7_ties_are_sorted_by_transaction_id`, not
  `test_p7_ties_out_of_time_order`.
- **Inputs:** minimal hand-built tables from `tests/builders.py`, changing only the fields the
  behaviour depends on. Cases cover each kind of input and each boundary, e.g. just below, at
  and just above a threshold.
- **Expected values are written out,** never computed by logic in the test.
- **Enforced: registered markers only.** A test that needs the downloaded dataset is marked
  `@pytest.mark.data`; CI skips these.
- **Enforced: at least 80% branch coverage** of `src/` as a whole, measured with `pytest-cov`.
  The minimum is raised as coverage rises and never lowered to let a change through.

## Data

- **Data contracts.** Each dataset passed from one bounded context to another (e.g. prepared
  transactions, labels, features, scores), and each input a component relies on (e.g. typed
  transactions entering preparation), has a data contract: its producer and consumers, its
  schema (column names, dtypes, nullability and value ranges) and its quality rules. The schema
  is declared with `pandera`, and checked by the producer before writing and by the consumer on
  reading. So far the typed transactions contract is checked when preparation starts and the
  prepared transactions contract by P8 before the file would be written; no check on reading
  exists yet.

## Reproducibility

- **Notebooks stay thin.** They import from `mule_detection`, and explore or display results;
  logic used more than once moves into `src/`.

## Before a pull request

1. `make check` passes.
2. If code that produces data or reported figures changed (`src/mule_detection/source/`,
   `payments/` and `evaluation/` now; `detection/` later), the affected `make` targets are re-run
   on the real data, the `data` tests are run locally (`uv run pytest -m data`), and the headline
   figures still match the document that owns them.
3. If a notebook is affected, it runs from top to bottom.
4. If documentation changed, the documentation checks in `.claude/skills/docs-check/SKILL.md`
   pass.
5. Any departure from `scope_and_rationale.md` has a `docs/decisions.md` entry.
6. No data, credentials, notebook outputs, personal email addresses or local paths are committed.

The pull request description states what changed, why, and how it was verified, with the
commands run and the figures they produced.

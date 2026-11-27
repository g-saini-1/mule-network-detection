# Stage 1 and 2 targets. Later stages add rules, train, graph and evaluate.
.PHONY: setup data validate-data labels prepare-data test lint format typecheck check

setup:  ## install dependencies into .venv
	uv sync

data:  ## download the HI-Small files into data/raw (skips unchanged files), then validate them
	uv run python -m mule_detection.source.download
	$(MAKE) validate-data

validate-data:  ## run validation checks on the raw files
	uv run python -m mule_detection.source.validate

labels:  ## build account-level mule labels into data/processed
	uv run python -m mule_detection.evaluation.account_labels

prepare-data:  ## prepare the raw transactions into data/interim/transactions.parquet
	uv run python -m mule_detection.source.prepare_transactions

test:  ## run the test suite
	uv run pytest

lint:  ## check code style
	uv run ruff check src tests

format:  ## reformat code in place
	uv run ruff format src tests

typecheck:  ## type-check the package
	uv run mypy

check:  ## everything CI runs: format check, lint, type check, tests
	uv run ruff format --check src tests
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

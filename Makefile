# Stage 1 targets. Later stages add rules, train, graph and evaluate.
.PHONY: setup data validate-data test lint

setup:  ## install dependencies into .venv
	uv sync

data:  ## download the HI-Small files into data/raw (skips unchanged files), then validate them
	uv run python -m mule_detection.data.download
	$(MAKE) validate-data

validate-data:  ## run validation checks on the raw files
	uv run python -m mule_detection.data.validate

test:  ## run the test suite
	uv run pytest

lint:  ## check code style
	uv run ruff check src tests

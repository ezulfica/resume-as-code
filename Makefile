.PHONY: install test run clean lint

install:
	uv sync

lint:
	# Check all YAML files in config, commons and resumes
	uv run yamllint .

test:
	uv run python -m pytest

run:
	uv run python main.py

clean:
	rm -rf dist/*
	rm -rf temp_dir/

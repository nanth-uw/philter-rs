default:
    @just --list

build:
    uv run maturin build --uv

develop:
    uv run maturin develop --uv

test:
    uv run pytest

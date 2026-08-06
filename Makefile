# Relay development tooling.
# Requires: uv (https://docs.astral.sh/uv), Python >= 3.11.

UV ?= uv

.PHONY: help all test lint typecheck format images

help: ## Show available targets
	@echo "relay targets:"
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

all: lint typecheck test ## Full pre-push gate

test: ## Run the test suite (pytest)
	$(UV) run pytest

lint: ## Ruff lint (zero-warning policy)
	$(UV) run ruff check .

typecheck: ## Static typecheck (mypy over src/)
	$(UV) run mypy src

format: ## Auto-format with ruff
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

images: ## Regenerate docs/images assets (PIL, deterministic)
	$(UV) run python docs/make_images.py

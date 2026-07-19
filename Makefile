.PHONY: help install dev lint typecheck test check build run restart clean

IMAGE      ?= nodewatch
CONTAINER  ?= nodewatch-container
PORT       ?= 8000

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime dependencies (pipenv)
	pipenv install --deploy

dev: ## Install runtime + dev dependencies
	pip install -r requirements-dev.txt

lint: ## Run ruff
	ruff check app tests

typecheck: ## Run mypy
	mypy app

test: ## Run the test suite
	pytest

check: lint typecheck test ## Run lint, type-check and tests

build: ## Build the Docker image
	docker build --tag $(IMAGE) .

run: ## Run the API locally with hot reload
	uvicorn app.api.app:create_app --factory --reload --port $(PORT)

restart: build ## Rebuild and restart the container
	docker stop $(CONTAINER) || true
	docker rm $(CONTAINER) || true
	docker run -d -p $(PORT):8000 --name $(CONTAINER) $(IMAGE)

clean: ## Remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

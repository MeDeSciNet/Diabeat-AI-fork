.DEFAULT_GOAL := help
SHELL := /bin/bash
PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
VENV ?= .venv

# Local (non-docker) runs use SQLite and the filesystem object store, so every
# target below works with nothing installed but Python and Node.
export DATABASE_URL ?= sqlite:///./data/somno.db
export LOCAL_STORAGE_DIR ?= ./data/objects
export CELERY_TASK_ALWAYS_EAGER ?= true
export API_AUTH_REQUIRED ?= false

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ------------------------------------------------------------------ setup
$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip

.PHONY: install
install: $(VENV)/bin/python ## Install every Python package plus frontend deps
	$(PIP) install --quiet -e packages/shared-schemas -e packages/sim -e packages/ing -e packages/pam
	$(PIP) install --quiet pytest pytest-asyncio httpx
	npm install --no-audit --no-fund

.PHONY: schemas
schemas: ## Regenerate Python and TypeScript types from the JSON Schemas
	python3 packages/shared-schemas/codegen.py

.PHONY: schemas-check
schemas-check: schemas ## Fail if the generated types have drifted from the schemas
	@git diff --exit-code packages/shared-schemas/generated \
	  || (echo "generated types are stale - run 'make schemas' and commit"; exit 1)

# ------------------------------------------------------------------ tests
.PHONY: test
test: test-py test-web ## Run every test suite

.PHONY: test-py
test-py: ## Python tests (SIM, ING, PAM)
	$(PY) -m pytest packages/sim/tests packages/ing/tests packages/pam/tests

.PHONY: test-fast
test-fast: ## Python tests, skipping the slow full-pipeline scenarios
	$(PY) -m pytest packages/sim/tests packages/pam/tests \
	  packages/ing/tests -k "not f1_meets and not sensor_failure_night"

.PHONY: test-web
test-web: ## Frontend tests, including the forbidden-terminology lint
	npm run test --workspace @somno/web-shared

.PHONY: lint-terms
lint-terms: ## Check UI copy for forbidden clinical terminology (PRD 2.1 R3)
	npm run lint:terms

.PHONY: build-web
build-web: ## Build both frontends (lint runs first and can fail the build)
	npm run build

# ------------------------------------------------------------- dev running
.PHONY: bench
bench: ## Detection metrics for every scenario against ground truth
	$(PY) -m somno_ing.cli bench --duration-min 180 --out out/bench.json

.PHONY: sim
sim: ## Generate one night to ./out (no broker needed)
	$(PY) -m somno_sim.cli run --scenario healthy_adult --seed 42 --speed 0 --out out/session

.PHONY: seed
seed: ## Create demo beds and subjects
	$(PY) -m somno_ing.cli seed-demo --beds 12

# -------------------------------------------------------------------- demo
.PHONY: demo
demo: ## End-to-end walkthrough: SIM -> ING -> risk -> alerts -> PAM (PRD 12)
	$(PY) scripts/demo.py

.PHONY: demo-docker
demo-docker: ## Same walkthrough against a running docker compose stack
	$(PY) scripts/demo.py --remote

# ------------------------------------------------------------------ docker
.PHONY: up
up: ## Start the whole stack
	docker compose up -d --build

.PHONY: down
down: ## Stop the stack
	docker compose down

.PHONY: logs
logs: ## Follow service logs
	docker compose logs -f --tail=100

.PHONY: sim-docker
sim-docker: ## Run a SIM night into the running stack over MQTT
	docker compose --profile sim run --rm sim

.PHONY: clean
clean: ## Remove local run artefacts
	rm -rf data out .pytest_cache
	find packages -name __pycache__ -type d -prune -exec rm -rf {} +

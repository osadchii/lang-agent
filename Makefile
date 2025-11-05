.PHONY: backend-install backend-dev backend-api backend-test stack-db stack-docker frontend-install frontend-dev frontend-build

PYTHON := $(shell command -v python3 2>/dev/null)
ifeq ($(PYTHON),)
PYTHON := $(shell command -v python 2>/dev/null)
endif
ifeq ($(PYTHON),)
$(error Python interpreter not found. Install python3 or python before running make targets.)
endif

backend-install:
	$(PYTHON) -m pip install -e .
	$(PYTHON) -m pip install -r requirements-dev.txt

backend-dev:
	$(PYTHON) -m backend.cli

backend-api:
	uvicorn backend.api.app:create_api --factory --reload

backend-test:
	pytest

stack-db:
	docker compose up -d postgres

stack-docker:
	docker compose up --pull always

frontend-install:
	npm --prefix apps/frontend install

frontend-dev: frontend-install
	npm --prefix apps/frontend run dev

frontend-build: frontend-install
	npm --prefix apps/frontend run build

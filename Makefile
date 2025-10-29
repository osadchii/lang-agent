.PHONY: backend-install backend-dev backend-test stack-db stack-docker frontend-install frontend-dev frontend-build

backend-install:
	pip install -e .
	pip install -r requirements-dev.txt

backend-dev:
	python -m backend.cli

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

.PHONY: backend-install backend-dev backend-api backend-test stack-db stack-docker frontend-install frontend-dev frontend-build

backend-install:
	pip install -e .
	pip install -r requirements-dev.txt

backend-dev:
	python -m backend.cli

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

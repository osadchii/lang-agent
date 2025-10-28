.PHONY: backend-dev backend-test stack-docker frontend-install frontend-dev frontend-build

backend-dev:
	python -m backend.cli

backend-test:
	pytest

stack-docker:
	docker compose up --pull always

frontend-install:
	npm --prefix apps/frontend install

frontend-dev: frontend-install
	npm --prefix apps/frontend run dev

frontend-build: frontend-install
	npm --prefix apps/frontend run build

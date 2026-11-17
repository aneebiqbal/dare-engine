VENV := .venv
PYTHON := $(VENV)/bin/python

# Tests run with the test-only development sign-in enabled. The default run
# (docker compose up) keeps DEV_AUTH_ENABLED off.
TEST_ENV := DEV_AUTH_ENABLED=true NEXT_PUBLIC_DEV_AUTH=1

.PHONY: up down logs accept test check web-accept screens doctor create-admin voice contract types

up:
	docker compose up -d --wait --build

down:
	docker compose down

logs:
	docker compose logs --tail=100 -f

$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r tests/requirements.txt

# Acceptance tests are the definition of done.
accept: $(VENV)/bin/python
	$(TEST_ENV) docker compose up -d --wait --build
	$(VENV)/bin/python -m pytest tests/acceptance --ignore=tests/acceptance/test_web_pages.py -v

test: $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests -v

# Fail if the mock layer leaks into application code.
check: $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests/unit/test_no_mock.py -v

# Web page flows and accessibility against the real backend.
web-accept: $(VENV)/bin/python
	$(TEST_ENV) docker compose up -d --wait --build
	$(VENV)/bin/python -m pytest tests/acceptance/test_web_pages.py -v
	$(VENV)/bin/python tests/screenshots/a11y.py

screens: $(VENV)/bin/python
	NEXT_PUBLIC_API_MOCK=1 docker compose up -d --wait --build
	$(VENV)/bin/python tests/screenshots/capture.py
	$(VENV)/bin/python tests/screenshots/a11y.py
	NEXT_PUBLIC_API_MOCK=0 docker compose up -d --wait --build

# Environment and connection checks. Prints PASS/FAIL, never a value.
doctor:
	docker compose exec -T api python -m app.doctor

# Create the first admin. Prompts for the password; never takes it as an argument.
create-admin:
	docker compose exec -T api python -m app.create_admin

# Download the local TTS voice model (Piper, MIT).
voice:
	docker compose exec -T worker python -m app.voice $(if $(VOICE),$(VOICE),en_US-amy-medium)

# Regenerate the OpenAPI contract from the implemented routes.
contract:
	docker compose exec -T api python -m app.export_contract
	docker compose cp api:/app/contracts/openapi.yaml contracts/openapi.yaml

# Regenerate the typed web client from the contract.
types:
	cd web && npx --yes openapi-typescript ../contracts/openapi.yaml -o lib/api-types.ts

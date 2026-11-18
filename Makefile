VENV := .venv
PYTHON := $(VENV)/bin/python

# Tests run with the test-only development sign-in enabled. The default run
# (docker compose up) keeps DEV_AUTH_ENABLED off.
# Tests run on the recorded AI provider; set LLM_PROVIDER=openai in .env for a
# live local run.
TEST_ENV := DEV_AUTH_ENABLED=true NEXT_PUBLIC_DEV_AUTH=1 LLM_PROVIDER=recorded

.PHONY: up down logs accept test check web-accept screens budgets doctor create-admin voice cleanup contract types

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

# Fail if the mock layer leaks into app code, or a GPL/AGPL dep is in the core.
check: $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests/unit/test_no_mock.py tests/unit/test_licence.py -v

# Print the licence audit on its own.
licence: $(VENV)/bin/python
	$(VENV)/bin/python tests/licence_check.py

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

# Web performance budgets on the five most-used pages.
budgets: $(VENV)/bin/python
	$(VENV)/bin/python tests/screenshots/budgets.py

# Environment and connection checks. Prints PASS/FAIL, never a value.
doctor:
	docker compose exec -T api python -m app.doctor

# Create the first admin. Prompts for the password; never takes it as an argument.
create-admin:
	docker compose exec -T api python -m app.create_admin

# OPTIONAL voice-over add-on (GPL piper-tts). Installs into the running worker
# and downloads the voice model. Not part of the default build.
voice:
	docker compose exec -T worker sh -c "pip install -q -r /app/requirements-voice.txt && python -m app.voice $(if $(VOICE),$(VOICE),en_US-amy-medium)"

# Delete recordings and previews past the retention window.
cleanup:
	docker compose exec -T api python -c "from app.retention import sweep; print(sweep())"

# Regenerate the OpenAPI contract from the implemented routes.
contract:
	docker compose exec -T api python -m app.export_contract
	docker compose cp api:/app/contracts/openapi.yaml contracts/openapi.yaml

# Regenerate the typed web client from the contract.
types:
	cd web && npx --yes openapi-typescript ../contracts/openapi.yaml -o lib/api-types.ts

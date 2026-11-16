VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: up down logs accept test lint

up:
	docker compose up -d --wait --build

down:
	docker compose down

logs:
	docker compose logs --tail=100 -f

$(VENV)/bin/python:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r tests/requirements.txt

# Acceptance tests are the definition of done. Brings the stack up first.
# Web page flows run separately under `make web-accept` against the mock layer.
accept: up $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests/acceptance --ignore=tests/acceptance/test_web_pages.py -v

test: $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests -v

# Web sprint: page flows and accessibility run against the mock layer
# (NEXT_PUBLIC_API_MOCK=1) for pages whose backend is blocked by Gate 0.
web-accept: $(VENV)/bin/python
	NEXT_PUBLIC_API_MOCK=1 docker compose up -d --wait --build
	$(VENV)/bin/python -m pytest tests/acceptance/test_web_pages.py -v
	$(VENV)/bin/python tests/screenshots/a11y.py
	NEXT_PUBLIC_API_MOCK=0 docker compose up -d --wait --build

screens: $(VENV)/bin/python
	NEXT_PUBLIC_API_MOCK=1 docker compose up -d --wait --build
	$(VENV)/bin/python tests/screenshots/capture.py
	$(VENV)/bin/python tests/screenshots/a11y.py
	NEXT_PUBLIC_API_MOCK=0 docker compose up -d --wait --build

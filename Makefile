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
accept: up $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests/acceptance -v

test: $(VENV)/bin/python
	$(VENV)/bin/python -m pytest tests -v

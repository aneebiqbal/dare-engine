VENV := .venv
PYTHON := $(VENV)/bin/python

# Tests run with the test-only development sign-in enabled. The default run
# (docker compose up) keeps DEV_AUTH_ENABLED off.
# Tests run on the recorded AI provider; set LLM_PROVIDER=openai in .env for a
# live local run.
# The acceptance suite makes more requests per minute than the production rate
# limit allows, so the test run raises the ceiling. Production keeps the
# defaults from .env.example.
TEST_ENV := DEV_AUTH_ENABLED=true NEXT_PUBLIC_DEV_AUTH=1 LLM_PROVIDER=recorded \
	RATE_LIMIT_REQUESTS=100000 RATE_LIMIT_AUTH=100000

.PHONY: up down logs accept test check web-accept screens budgets doctor create-admin voice cleanup contract types research setup-engine research-local ssd-bridge mlx-bridge flow backup desktop vision-model vision-run

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
	NEXT_PUBLIC_API_MOCK=1 RATE_LIMIT_REQUESTS=100000 RATE_LIMIT_AUTH=100000 docker compose up -d --wait --build
	$(VENV)/bin/python tests/screenshots/capture.py
	$(VENV)/bin/python tests/screenshots/a11y.py
	NEXT_PUBLIC_API_MOCK=0 docker compose up -d --wait --build

# Web performance budgets on the five most-used pages.
budgets: $(VENV)/bin/python
	$(VENV)/bin/python tests/screenshots/budgets.py

# The end-to-end product journey, screenshots into docs/screens/flow/.
flow: $(VENV)/bin/python
	$(TEST_ENV) docker compose up -d --wait --build
	$(VENV)/bin/python tests/screenshots/flow.py

# Environment and connection checks. Prints PASS/FAIL, never a value.
doctor:
	docker compose exec -T api python -m app.doctor

# Create the first admin. Prompts for the password; never takes it as an argument.
create-admin:
	docker compose exec -T api python -m app.create_admin

# OPTIONAL voice-over add-on (GPL piper-tts). Installs into the running worker
# and downloads the voice model. Not part of the default build.
voice:
	docker compose exec -T worker sh -c "pip install -q -r /app/requirements-voice.txt && python -m worker_app.voice $(if $(VOICE),$(VOICE),en_US-amy-medium)"

# Delete recordings and previews past the retention window.
cleanup:
	docker compose exec -T api python -c "from app.retention import sweep; print(sweep())"

# Build the admin desktop app (Tauri). Artifact in desktop/src-tauri/target/.
desktop:
	cd desktop && npm install && npm run tauri build

# Pull the optional vision model (Qwen2.5-VL-7B, Apache-2.0).
vision-model:
	ollama pull $(if $(VISION_MODEL),$(VISION_MODEL),qwen2.5vl:7b)

# Run the sampled vision pass on one recording and print the suggestions.
vision-run:
	.venv/bin/python local/vision_run.py $(FILE) vision-out

# Dump the database to backups/ (see docs/deploy-web.md for the schedule).
backup:
	@bash scripts/backup.sh

# Regenerate the OpenAPI contract from the implemented routes.
contract:
	docker compose exec -T api python -m app.export_contract
	docker compose cp api:/app/contracts/openapi.yaml contracts/openapi.yaml

# Regenerate the typed web client from the contract.
types:
	cd web && npx --yes openapi-typescript ../contracts/openapi.yaml -o lib/api-types.ts

# Run today's research for every enabled game that has not run yet.
research:
	docker compose exec -T api python -c "from app.research import daily_research; print(daily_research())"

# One-time local engine on this Mac: Ollama for the AI client, MLX Whisper for
# transcription. No cloud, no key, no credit.
ENGINE_MODEL ?= qwen3:8b
MLX_MODEL ?= mlx-community/whisper-large-v3-mlx
setup-engine:
	@command -v ollama >/dev/null 2>&1 || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }
	ollama pull $(ENGINE_MODEL)
	python3 -m venv $(HOME)/.clipdesk-engine
	$(HOME)/.clipdesk-engine/bin/pip install -q --upgrade pip
	$(HOME)/.clipdesk-engine/bin/pip install -q mlx-whisper
	@echo "AI:  LLM_PROVIDER=openai LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama LLM_MODEL=$(ENGINE_MODEL)"
	@echo "ASR: MLX_WHISPER_URL=http://host.docker.internal:8798 MLX_WHISPER_MODEL=$(MLX_MODEL)"
	@echo "Then: make mlx-bridge and make ssd-bridge"

# Host MLX Whisper bridge (the worker container cannot reach Metal).
mlx-bridge:
	@test -x $(HOME)/.clipdesk-engine/bin/python || { echo "Run make setup-engine first"; exit 1; }
	$(HOME)/.clipdesk-engine/bin/python local/mlx_bridge.py

# Prove the research brain against the local model (no Docker needed).
research-local:
	.venv/bin/python local/research_local.py

# Host-side SSD bridge: lists /Volumes and copies a chosen video into the inbox.
ssd-bridge:
	@mkdir -p $(HOME)/.clipdesk/ssd-inbox
	.venv/bin/python local/ssd_bridge.py

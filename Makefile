SHELL := /bin/bash

POETRY ?= poetry
APP_MODULE ?= app.main:app
HOST ?= 127.0.0.1
PORT ?= 8000
OUTPUT_DIR ?= output

.PHONY: install install-browser dev test lint format e2e clean-output

install:
	$(POETRY) install

install-browser:
	$(POETRY) run playwright install chromium

dev:
	$(POETRY) run uvicorn $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

test:
	$(POETRY) run pytest -q

lint:
	$(POETRY) run ruff check .

format:
	$(POETRY) run black .

clean-output:
	rm -rf $(OUTPUT_DIR)

e2e:
	@mkdir -p $(OUTPUT_DIR)
	@set -euo pipefail; \
	$(POETRY) run uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) > $(OUTPUT_DIR)/e2e-server.log 2>&1 & \
	PID=$$!; \
	trap 'kill $$PID 2>/dev/null || true' EXIT; \
	sleep 2; \
	curl -fsS http://$(HOST):$(PORT)/health > $(OUTPUT_DIR)/e2e-health.json; \
	curl -fsS -D $(OUTPUT_DIR)/e2e-json.headers -o $(OUTPUT_DIR)/e2e-json.pdf \
		-X POST http://$(HOST):$(PORT)/generate \
		-H "Content-Type: application/json" \
		-d '{"html":"<html><body><h1>E2E JSON</h1><p>PDF API</p></body></html>","css":"h1 { color: #2563eb; }","filename":"e2e-json"}'; \
	curl -fsS -D $(OUTPUT_DIR)/e2e-multipart.headers -o $(OUTPUT_DIR)/e2e-multipart.pdf \
		-X POST http://$(HOST):$(PORT)/generate \
		-F 'template_name=invoice.html' \
		-F 'data={"customer_name":"E2E Corp","invoice_number":"INV-E2E","items":[{"name":"Plan","quantity":1,"price":"$99.00"}],"total":"$99.00"}' \
		-F 'filename=e2e-multipart'; \
	test "$$(head -c 4 $(OUTPUT_DIR)/e2e-json.pdf)" = "%PDF"; \
	test "$$(head -c 4 $(OUTPUT_DIR)/e2e-multipart.pdf)" = "%PDF"; \
	echo "E2E passed. Artifacts are in $(OUTPUT_DIR)/"

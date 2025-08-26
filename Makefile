SHELL := /bin/bash
PY := python3
BACKEND := backend
ENV_FILE := .env.local

export PYTHONPATH := $(PWD)/backend

.PHONY: venv reqs redis api discovery-dry discovery-publish explain contenders clean help

help:
	@echo "AMC Trader Local Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  venv              Create virtual environment and install deps"
	@echo "  reqs              Install requirements in current environment"
	@echo ""
	@echo "Services:"
	@echo "  redis             Start Redis container on port 6379"
	@echo "  api               Start API server on port 8000"
	@echo ""
	@echo "Discovery:"
	@echo "  discovery-dry     Run discovery in trace mode (no Redis writes)"
	@echo "  discovery-publish Run discovery and publish to local Redis"
	@echo ""
	@echo "Testing:"
	@echo "  explain           Fetch /discovery/explain from API"
	@echo "  contenders        Fetch /discovery/contenders from API"
	@echo ""
	@echo "Environment variables:"
	@echo "  RELAXED=true      Use relaxed filtering thresholds"
	@echo "  LIMIT=20          Max candidates to return"
	@echo "  JSON=true         Include full JSON output"

venv:
	$(PY) -m venv .venv && source .venv/bin/activate && $(PY) -m pip install --upgrade pip && pip install -r $(BACKEND)/requirements.txt

reqs:
	pip install -r $(BACKEND)/requirements.txt

redis:
	@echo "Starting Redis container on port 6379..."
	docker run --rm -p 6379:6379 redis:7-alpine

api:
	@echo "Starting API server on port 8000..."
	cd $(BACKEND) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

discovery-dry:
	@echo "Running discovery in trace mode..."
	@if [ -f $(ENV_FILE) ]; then export $$(cat $(ENV_FILE) | grep -v '^#' | xargs); fi && \
	RELAXED=$${RELAXED:-true} LIMIT=$${LIMIT:-15} $(PY) scripts/discovery_trace.py

discovery-publish:
	@echo "Running discovery and publishing to Redis..."
	@if [ -f $(ENV_FILE) ]; then export $$(cat $(ENV_FILE) | grep -v '^#' | xargs); fi && \
	LIMIT=$${LIMIT:-15} $(PY) scripts/discovery_publish.py

explain:
	@echo "Fetching discovery explain from API..."
	@curl -s http://localhost:8000/discovery/explain | jq '.trace | {stages,counts_in,counts_out}' || echo "API not responding or jq not installed"

contenders:
	@echo "Fetching discovery contenders from API..."
	@curl -s http://localhost:8000/discovery/contenders | jq 'length, .[0] // {}' || echo "API not responding or jq not installed"

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .venv

# Example usage:
# make redis &                    # Start Redis in background
# make discovery-dry              # Test discovery without Redis writes
# RELAXED=true LIMIT=20 make discovery-publish  # Publish with custom params
# make api &                      # Start API in background  
# make explain                    # Check trace data via API
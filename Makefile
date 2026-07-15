# 배터리 기상 예보 — local profile L (§12.1). `make setup` once, then `make demo`.

PY := .venv/bin/python

.PHONY: setup demo db-regen backend frontend test eval lint golden

setup:  ## venv + Python deps + frontend deps
	python3.11 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt
	npm --prefix frontend install

demo: data/demo.db  ## seed DB → FastAPI :8000 → Vite :5173, one command (§8.5)
	@trap 'kill 0' INT TERM EXIT; \
	$(PY) -m uvicorn backend.app.main:app --port 8000 & \
	npm --prefix frontend run dev

data/demo.db:
	$(PY) -m simulator.generate --seed 42 --sessions 60 --out data/demo.db

db-regen:  ## force-regenerate the committed seed DB (content is seed-fixed §8.6)
	$(PY) -m simulator.generate --seed 42 --sessions 60 --out data/demo.db

backend:
	$(PY) -m uvicorn backend.app.main:app --reload --port 8000

frontend:
	npm --prefix frontend run dev

test:
	$(PY) -m pytest

eval:  ## quick-100 metrics (§13 M0 DoD)
	$(PY) -m eval.quick100

lint:
	.venv/bin/ruff check . && .venv/bin/black --check .
	npm --prefix frontend run lint && npm --prefix frontend run format

golden:  ## regenerate golden files after an intentional core change
	$(PY) -m tests.golden.regen

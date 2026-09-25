.DEFAULT_GOAL := help

.PHONY: help install app demo demo-json smoke claude test phoenix check status push

VENV         := .venv
VENV_BIN     := $(VENV)/bin
PYTHON       ?= python3.12
PHOENIX_PORT ?= 6006

# Fail with an actionable message instead of "no such file or directory"
# when the venv has not been created yet. Usage: $(call require,streamlit)
define require
@test -x $(VENV_BIN)/$(1) || { \
	echo "❌ $(VENV_BIN)/$(1) not found."; \
	echo "   This clone has no environment yet - run 'make install' first."; \
	exit 1; \
}
endef

help:
	@echo "🔥 PitchRoast Hackathon Command Center"
	@echo "======================================"
	@echo "  make install   - 📦 Create .venv and install everything from pyproject.toml"
	@echo "  make app       - 🚀 Run the Streamlit UI with Phoenix observability"
	@echo "  make demo      - ⚡ Run full live CLI demo with fable-5-1"
	@echo "  make demo-json - 🧾 Run the CLI demo with machine-readable output"
	@echo "  make smoke     - 🧪 Pre-stage check: make test, then make demo"
	@echo "  make claude    - 🤖 Launch Claude Code pair programmer (isolated)"
	@echo "  make test      - 🔑 Test Anthropic public API connectivity"
	@echo "  make phoenix   - 🔭 Open Arize Phoenix Tracing Dashboard in browser"
	@echo "  make check     - 🧹 Lint and fix code formatting (ruff)"
	@echo "  make status    - 📊 Show git status and recent commits"
	@echo "  make push      - 📦 Commit and push changes to GitHub"

# The target that makes a fresh clone (or a borrowed laptop) work.
install:
	@test -d $(VENV) || { \
		echo "📦 Creating $(VENV) with $(PYTHON)..."; \
		$(PYTHON) -m venv $(VENV) || { \
			echo "❌ Could not create $(VENV) with '$(PYTHON)'."; \
			echo "   Retry with an explicit interpreter, e.g. 'make install PYTHON=python3'."; \
			exit 1; \
		}; \
	}
	@if command -v uv >/dev/null 2>&1; then \
		echo "⚡ uv detected - installing project + obs + dev extras"; \
		VIRTUAL_ENV="$(CURDIR)/$(VENV)" uv pip install -e ".[obs,dev]"; \
	else \
		echo "🐍 Installing project + obs + dev extras with pip"; \
		$(VENV_BIN)/python -m pip install --upgrade pip; \
		$(VENV_BIN)/python -m pip install -e ".[obs,dev]"; \
	fi
	@echo ""
	@echo "✅ Environment ready. Next: ./set_key.sh sk-ant-... && make test"
	@echo "   (Tracing is optional - 'uv pip install -e .' alone runs the app without Phoenix.)"

app:
	$(call require,streamlit)
	$(VENV_BIN)/streamlit run app.py

demo:
	$(call require,python)
	$(VENV_BIN)/python run_demo.py

# --json puts the raw verdict on stdout and all human output on stderr,
# so `make demo-json > verdict.json` yields a clean document.
demo-json:
	$(call require,python)
	$(VENV_BIN)/python run_demo.py --json

# Pre-stage check: connectivity first (cheap), then the full committee run.
smoke:
	@echo "🧪 Smoke check 1/2: API connectivity"
	@$(MAKE) --no-print-directory test
	@echo ""
	@echo "🧪 Smoke check 2/2: end-to-end demo"
	@$(MAKE) --no-print-directory demo
	@echo ""
	@echo "✅ Smoke check passed - safe to go on stage."

claude:
	@test -x ./claude_hackathon.sh || { echo "❌ ./claude_hackathon.sh missing or not executable."; exit 1; }
	./claude_hackathon.sh

test:
	$(call require,python)
	$(VENV_BIN)/python test_connection.py

# Phoenix runs in-process inside app.py / run_demo.py; there is no server to
# open unless one of those is already running. Probe before opening a tab.
phoenix:
	@if nc -z localhost $(PHOENIX_PORT) >/dev/null 2>&1; then \
		echo "🔭 Phoenix is live - opening http://localhost:$(PHOENIX_PORT)"; \
		open "http://localhost:$(PHOENIX_PORT)"; \
	else \
		echo "⚠️  Nothing is listening on localhost:$(PHOENIX_PORT)."; \
		echo "   Phoenix is launched in-process: start 'make app' or 'make demo' first,"; \
		echo "   then re-run 'make phoenix'. (Override with 'make phoenix PHOENIX_PORT=…'.)"; \
	fi

# --isolated was dropped on purpose: it ignores pyproject.toml *and* enables
# ruff 0.16's broad default rule set (S/BLE/EXE/RUF100), which flags the
# deliberate "# noqa: BLE001" handlers as errors. The [tool.ruff] section now
# owns the rule selection.
check:
	$(call require,ruff)
	$(VENV_BIN)/ruff check --fix .

status:
	git status -s
	@echo ""
	git log -n 3 --oneline

push:
	@echo "📋 Working tree:"
	@git status -s
	@echo ""
	@read -p "Stage ALL of the above with 'git add .'? [y/N] " ok; \
	case "$$ok" in \
		y|Y|yes|YES) ;; \
		*) echo "🚫 Aborted - nothing staged."; exit 0;; \
	esac; \
	read -p "Commit message: " msg; \
	if [ -z "$$msg" ]; then \
		echo "🚫 Empty commit message - aborted, nothing staged."; \
		exit 0; \
	fi; \
	git add .; \
	git commit -m "$$msg" && git push origin main

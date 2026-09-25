.PHONY: help app demo claude check test phoenix push status

VENV_BIN := .venv/bin

help:
	@echo "🔥 PitchRoast Hackathon Command Center"
	@echo "======================================"
	@echo "  make app       - 🚀 Run the Streamlit UI with Phoenix observability"
	@echo "  make demo      - ⚡ Run full live CLI demo with fable-5-1"
	@echo "  make claude    - 🤖 Launch Claude Code pair programmer (isolated)"
	@echo "  make test      - 🔑 Test Anthropic public API connectivity"
	@echo "  make phoenix   - 🔭 Open Arize Phoenix Tracing Dashboard in browser"
	@echo "  make check     - 🧹 Lint and fix code formatting (ruff)"
	@echo "  make status    - 📊 Show git status and recent commits"
	@echo "  make push      - 📦 Commit and push changes to GitHub"

app:
	$(VENV_BIN)/streamlit run app.py

demo:
	$(VENV_BIN)/python run_demo.py

claude:
	./claude_hackathon.sh

test:
	$(VENV_BIN)/python test_connection.py

phoenix:
	open http://localhost:6006

check:
	$(VENV_BIN)/ruff check --fix --isolated .

status:
	git status -s
	@echo ""
	git log -n 3 --oneline

push:
	@read -p "Enter commit message: " msg; \
	git add .; \
	git commit -m "$$msg"; \
	git push origin main

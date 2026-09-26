# Contributing to PitchRoast 🔥

Welcome! Thank you for your interest in contributing to **PitchRoast**.

PitchRoast was created for the **Stockholm | Fable 5.1 x Opus 5.5 Build Day** presented by the **Claude Community Stockholm**. We welcome contributions from developers, designers, prompt engineers, and startup founders of all skill levels!

---

## 🧭 Project Ethos & Values

1. **Delight & Humor**: We build software that makes people laugh while providing genuinely useful feedback on startup pitches.
2. **Defensive Reliability**: Zero-crash philosophy. Any new feature must handle network timeouts, rate limits, and malformed LLM responses gracefully.
3. **Clean Architecture**: Multi-agent fan-out logic belongs in `syndicate.py`, UI presentation belongs in `founder.py` / `board.py` / `ui.py`, and telemetry belongs in `observability.py`.

---

## 🛠️ Development Setup

### Prerequisites
- Python 3.12+
- `uv` (recommended) or standard `python3` / `pip`
- Git

### 1. Fork & Clone
```zsh
git clone https://github.com/<your-username>/pitchroast.git
cd pitchroast
```

### 2. Set Up Virtual Environment
Using `uv`:
```zsh
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[obs,dev]"
```
Or using the `Makefile`:
```zsh
make install
```

### 3. Configure API Keys
Copy the example environment file:
```zsh
cp .env.example .env
```
Add your `ANTHROPIC_API_KEY` (and optionally `ELEVENLABS_API_KEY`).
*Note: You can run offline tests and the fallback demo completely without an API key!*

### 4. Install Pre-Commit Hooks
```zsh
pre-commit install
```

---

## 🧪 Testing & Quality Gates

Before opening a pull request, ensure all tests and lints pass:

```zsh
# Run all offline test suites (no API key needed)
make test

# Or run individual suites
python test_modes.py
python test_syndicate.py
python test_ui.py
python test_observability.py

# Lint & format code
make check
# or
ruff check --fix .
```

---

## 🎭 How to Add a New VC Persona

One of the easiest and most fun ways to contribute is by adding a new VC partner archetype!

1. Open `syndicate.py`.
2. Define your partner's prompt, temperament, and rubric in `DEFAULT_PERSONAS`:
   ```python
   "my_new_persona": {
       "name": "Astrid Lindgren",
       "firm": "Nordic Fairy Tale Ventures",
       "tone": "Warm but brutally honest reality check",
       "temperature": 0.7,
       "focus": "Product-market fit and genuine customer love",
   }
   ```
3. Add a corresponding test in `test_syndicate.py`.
4. Run `make test` to verify.

---

## 📬 Submitting a Pull Request

1. Create a feature branch:
   ```zsh
   git checkout -b feature/my-awesome-improvement
   ```
2. Commit your changes with clear, descriptive commit messages:
   ```zsh
   git commit -m "feat(syndicate): add Nordic Climate Tech VC persona"
   ```
3. Push to your fork:
   ```zsh
   git push origin feature/my-awesome-improvement
   ```
4. Open a Pull Request using our [PR Template](.github/pull_request_template.md).
5. Ensure GitHub CI checks pass!

---

## 📜 Code of Conduct
Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions within this project.

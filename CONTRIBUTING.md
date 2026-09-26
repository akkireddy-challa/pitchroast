# Contributing to PitchRoast 🔥

Thank you for your interest in contributing to PitchRoast!

PitchRoast was built for the **Stockholm | Fable 5.1 x Opus 5.5 Build Day** presented by the **Claude Community Stockholm**.

## 🚀 How to Contribute

1. **Fork the Repository**:
   Click the "Fork" button at the top right of this repository.

2. **Clone your fork**:
   ```zsh
   git clone https://github.com/<your-username>/pitchroast.git
   cd pitchroast
   ```

3. **Set up the virtual environment**:
   ```zsh
   uv venv .venv
   source .venv/bin/activate
   uv pip install -e ".[obs,dev]"
   ```

4. **Run the automated test suites**:
   ```zsh
   python test_modes.py
   python test_syndicate.py
   python test_ui.py
   python test_observability.py
   ```

5. **Lint your changes**:
   ```zsh
   ruff check .
   ```

6. **Submit a Pull Request**:
   Describe your feature, comedic roast persona, or architectural improvement, and ensure all tests pass cleanly.

## ⚖️ Code of Conduct
Be constructive, humorous, and respectful to fellow builders.

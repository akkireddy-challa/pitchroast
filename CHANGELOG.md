# Changelog

All notable changes to **PitchRoast** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-26

### 🚀 Added
- **Multi-Agent VC Committee Engine**:
  - Parallel async fan-out with 3 specialized partner agents (*Sven Lindström*, *Balthazar Sterling*, *Nova Spark*).
  - Lead Partner synthesizer producing structured consensus verdicts and predatory term sheets.
- **Dual Operating Modes**:
  - **Founder Hotseat**: Clean, founder-facing roast dashboard with soundboard, score badges, and term sheet PDF download.
  - **Syndicate Observatory**: Admin & judge telemetry view with live Phoenix tracing, latency monitors, and temperature sliders.
- **Arize Phoenix Observability**:
  - Full OpenTelemetry span hierarchy tracing every partner call, token counts, latency, and cost calculation.
  - In-process Phoenix server integration.
- **Interactive 3D Pitch Deck**:
  - Reveal.js + Three.js interactive presentation deck at `docs/index.html` with animated particle background, keyboard navigation, and live audio integration.
- **Voice & Narration**:
  - ElevenLabs speech synthesis integration for realistic audio roasts and founder pitch playback.
- **PDF Term Sheet Generator**:
  - Dynamic generation of realistic investor term sheets using ReportLab.
- **Zero-Crash Resilience**:
  - Offline fallback engine ensuring 100% demo reliability under Wi-Fi loss or API rate limits.
- **Open Source Community Lifecycle**:
  - Comprehensive documentation: `ARCHITECTURE.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `LICENSE` (MIT).
  - GitHub Issue & Pull Request templates (`feature_request.md`, `bug_report.md`, `new_vc_persona.md`, `pull_request_template.md`).
  - Pre-commit hooks for Ruff formatting and linting.
  - Automated test suites (`test_modes.py`, `test_syndicate.py`, `test_ui.py`, `test_observability.py`).

---

[1.0.0]: https://github.com/akkireddy-challa/pitchroast/releases/tag/v1.0.0

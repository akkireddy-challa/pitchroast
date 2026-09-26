# 🗺️ PitchRoast Product Roadmap

Welcome to the future of **PitchRoast**! This roadmap outlines our planned milestones, feature evolutions, and community initiatives.

---

## 📍 Current Release: v1.0.0 (Stockholm Build Day MVP)
- [x] **Multi-Agent VC Committee**: Parallel fan-out evaluation across 3 distinct partner personas (Sven, Balthazar, Nova) + Lead Partner synthesis.
- [x] **Dual Operating Modes**:
  - **Founder Hotseat**: Clean, founder-facing roast dashboard with soundboard, score badges, and term sheet.
  - **Syndicate Observatory**: Admin & judge telemetry view with live Phoenix tracing, latency monitors, and temperature sliders.
- [x] **3D Interactive Pitch Deck**: Reveal.js + Three.js interactive presentation deck at `docs/index.html` and GitHub Pages.
- [x] **ElevenLabs Voice Pitching**: High-fidelity narration for partner roasts.
- [x] **ReportLab Term Sheet Generator**: Dynamic investor term sheet PDF generation.
- [x] **Arize Phoenix Observability**: Complete OpenTelemetry span instrumentation with token accounting and eval metrics.
- [x] **Zero-Crash Resilience**: Deterministic mock fallbacks on network dropouts or Anthropic 429 rate limits.

---

## 🚀 Near-Term: v1.1.0 (Realtime Voice & Community Personas)
- [ ] **Realtime Two-Way Voice**:
  - Enable live interruptible voice pitches using WebRTC and streaming speech-to-speech models.
  - Founders can speak their pitch into the microphone and get immediately interrupted by Balthazar or Sven.
- [ ] **Community Persona Marketplace**:
  - Allow community members to contribute custom VC personas via JSON / YAML without modifying core engine code.
  - Archetypes: *Crypto Degen Angel*, *Biotech PI*, *Enterprise Procurement Officer*, *Silicon Valley Influencer*.
- [ ] **Export to Notion & Slack**:
  - 1-click export of term sheets and roast critiques directly into a startup's Notion workspace or Slack channel.

---

## 🔮 Medium-Term: v1.2.0 (Multimodal Pitch Deck Vision Critique)
- [ ] **Slide-by-Slide Vision Analysis**:
  - Ingest PDF or slide image files directly into Claude 3.5 Sonnet's vision model.
  - Identify terrible typography, unreadable 4-font cap tables, and fake traction curves.
- [ ] **Interactive Cap Table Stress Tester**:
  - Interactive slider showing how founder equity dilutes to 2.4% after accepting the Syndicate's predatory convertible note.

---

## 🌟 Long-Term: v2.0.0 (Global Roast Syndicate & Multiplayer)
- [ ] **Multiplayer Founder Hotseat**:
  - Live spectator room where friends and accelerators can watch a founder pitch live on stage.
  - Real-time emoji reactions ("💀 RIP", "🔥 Cooked", "🚀 100x") and audience Delusion Voting.
- [ ] **Delusion Hall of Fame**:
  - Anonymous leaderboard of the most ambitious, hilarious, or wildly valued startup pitches submitted by the community.
- [ ] **Self-Hosted Docker Compose Stack**:
  - Single-line `docker compose up` spinning up PitchRoast, Arize Phoenix, and a local Ollama / vLLM bridge.

---

## 🤝 Contributing to the Roadmap
Have an idea or want to sponsor a milestone? Check out our [Contributing Guidelines](CONTRIBUTING.md) or open a [Feature Request](https://github.com/akkireddy-challa/pitchroast/issues/new?template=feature_request.md)!

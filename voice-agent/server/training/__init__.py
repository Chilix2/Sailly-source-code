"""
Training module -- Multi-phase audio training loop components.

Modules:
  - audio_injector: Audio synthesis, noise, STT validation
  - tier1_runner: Phase 1 text-mode testing
  - tier2_runner: Phase 2 audio round-trip
  - switch_runner: Phase 3 tier-switch edge cases
  - competitor_runner: Phase 4 OpenAI comparison
  - scoring: Multi-dimensional scoring engine
  - report_writer: Report generation and output
"""

# Production and Legacy Code Manifest

Last audited: 2026-05-26

This manifest classifies the current repository so cleanup can keep the live
voice agent small without losing validation tooling that is still useful.

## Production Runtime

These paths are part of the live `/ws/demo` service or its startup/finalization
path and must remain in the production source tree.

- `server/main.py`
- `server/brain_service.py`
- `server/brain/v4_turn_processor.py`
- `server/brain/v4_pipeline.py`
- `server/brain/conversation_state.py`
- `server/brain/slot_extractor.py`
- `server/brain/slot_extraction_layer.py`
- `server/brain/slot_validators.py`
- `server/brain/validation_registry.py`
- `server/brain/speculative_executor.py`
- `server/brain/intent_classifier.py`
- `server/brain/intent_session.py`
- `server/brain/worker_router.py`
- `server/brain/worker_executor.py`
- `server/brain/workers/`
- `server/brain/context_doc_builder.py`
- `server/brain/tiny_generator.py`
- `server/brain/filler_scheduler.py`
- `server/brain/backchannel_injector.py`
- `server/brain/tts_conditioning.py`
- `server/brain/stt/`
- `server/brain/observability/`
- `server/brain/layer1/persist.py`
- `server/brain/layer1/text_mode_runner.py`
- `server/brain/layer1/validation/`
- `server/brain/health.py`
- `server/brain/rate_limit.py`
- `server/brain/logging_config.py`
- `server/brain/call_summary.py`
- `server/providers/`
- `server/tools/`
- `tools/executor.py`
- `tools/sms_service.py`
- `server/sailly_gemini_tts.py`
- `server/barge_in_handler.py`
- `server/browser_serializer.py`
- `server/audio_recorder.py`
- `server/core/`
- `server/configs/`
- `server/session.py`
- `server/database.py`
- `server/monitoring.py`
- `server/live_call_trace.py`
- `server/transcript_purge.py`
- `server/call_report/`
- `server/call_auditor_live.py`
- `server/builder/`
- `server/tenants/`
- `configs/tenants/`
- `configs/providers/`
- `configs/industry_packs/`
- `configs/rate_limit_overrides.txt`
- `frontend/`
- `migrations/`
- `deploy/`
- `scripts/`
- `systemd/`

## Tooling Kept in Repository

These files are not part of the hot voice path, but they are intentionally kept
because they support validation, failure discovery, smoke tests, or operational
debugging.

- `server/validation/`
- `server/training/`
- `server/scenarios/`
- `server/failure_ingestor.py`
- `server/metrics_reporter.py`
- `test-infra/`
- `tests/`
- `server/tests/`
- `run_validation.sh`
- `run_phase_a.sh`
- `run_focused_reruns.py`
- `quick_smoke_reruns.py`
- `run_light_discovery_all_phases.py`
- `test_failure_ingestor_smoke.py`

## Legacy Removed

The old ADK/node-manager stack is not the live turn processor. Production uses
`V4TurnProcessor` from `server/brain/v4_turn_processor.py`, imported under the
compatibility name `ADKTurnProcessor` inside `server/brain_service.py`.

The session-restore helper formerly imported from `server/brain/adk_turn_processor.py`
has been extracted to `server/brain/session_restore.py`, so the legacy stack is
no longer required for production reconnects.

Removed legacy runtime files:

- `server/brain/adk_turn_processor.py`
- `server/brain/node_manager.py`
- `server/brain/conversation_nodes.py`
- `server/brain/tier2_runner.py`
- `server/brain/memory_manager.py`
- `server/brain/captured_intents_legacy.py`
- `server/brain/call_auditor_de.py`
- `server/brain/context_inspector.py`
- `server/brain/proactive_utterances.py`
- `server/brain/state_migrations.py`
- `server/brain/layer1/nodes/`
- `server/brain/layer1/node_manager.py`
- `server/brain/layer1/forced_commits/`
- `server/brain/layer1/after_hours.py`
- `server/brain/layer1/confidence_guard.py`
- `server/brain/layer1/goodbye_state_machine.py`
- `server/brain/layer1/identifier_lookup.py`
- `server/brain/layer1/intent_advance.py`
- `server/brain/layer1/intent_routing.py`
- `server/brain/layer1/turn_control.py`
- `server/brain/layer1/turn_package_builder.py`
- `server/brain/layer1/turn_runner.py`
- `server/brain/layer1/voice_conditioning.py`
- `server/brain/layer2/`
- `server/brain/layer3/`

## Archive or Never Commit

These paths are not needed for production runtime and should stay out of future
GitHub production snapshots unless explicitly needed for historical analysis.

- `.env`
- `.env.local`
- `credentials/`
- `call_reports/`
- `reports/`
- `logs/`
- `venv/`
- `*.bak`
- `ANALYSIS_REPORT.json`
- `COMPLETION_REPORT.txt`
- `VERIFICATION_COMPLETE.txt`
- `PHASE_1_READY_FOR_TRACE.txt`

## GitHub Layout Rule

The live host uses the flat tree at `/home/charles2/sailly-browser-demo`.
GitHub stores that same tree under `voice-agent/`.

Do not push a root-level duplicate app tree to GitHub. The repository root is
reserved for wrapper metadata such as `.github/`, `.gitignore`, and an index
README.

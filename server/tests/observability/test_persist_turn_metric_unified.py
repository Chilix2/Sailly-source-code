"""
Unit tests for the unified persist_turn_metric() consolidation (Phase 1.6).

Tests all three execution paths:
  - "live": single live call, minimal columns, direct asyncpg connection
  - "finalize": batch finalization, full observability columns, pre-existing conn
  - "text_mode": text-only pipeline, delegates to database.persist_turn_metrics()
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_brain_service():
    """Create a mock BrowserBrainService instance."""
    from server.brain_service import BrowserBrainService

    service = MagicMock(spec=BrowserBrainService)
    service.call_sid = "test-call-123"
    service.tenant_id = "doboo"
    return service


@pytest.fixture
def sample_turn_metric():
    """Sample turn metric dict covering all three paths."""
    return {
        "turn_number": 1,
        "user_text": "Ich möchte bestellen",
        "bot_text": "Gerne! Was möchten Sie?",
        "stt_latency_ms": 150,
        "llm_latency_ms": 200,
        "tts_latency_ms": 100,
        "total_latency_ms": 450,
        "stt_ms": 150,
        "extract_ms": 50,
        "l2_ms": 200,
        "tool_ms": 0,
        "total_ms": 400,
        "tts_first_byte_ms": 50,
        "tts_ttfb_ms": 100,
        "tools_called": ["check_availability"],
        "node_name": "greeting",
        "stage3_text": "Gerne! Was möchten Sie?",
        "stt_confidence": 0.95,
        "validation_breakdown": {"DATUM": 1},
        "tts_situation": "casual",
        "tts_mood": "friendly",
        "layer1_decision": {"node": "greeting", "forced_tools": []},
        "layer2_raw_output": "Gerne! Was möchten Sie?",
        "layer3_changes": {"text_changed": False},
        # Finalize-only fields
        "prompt_tokens_in": 500,
        "prompt_tokens_out": 150,
        "max_output_tokens_config": 200,
        "temperature_config": 0.7,
        "top_p_config": 0.9,
        "slot_state_json": {"items": []},
        "slot_state_diff": {"added": [], "changed": []},
        "slots_filled_count": 0,
        "slots_confirmed_count": 0,
        "slots_missing_required": [],
        "validations_fired_this_turn": {"DATUM": 1},
        "validations_completed_this_turn": {},
        "validations_pending_end_of_turn": {},
        "validation_cancellations": 0,
        "raw_utterance_in_prompt": True,
        "prompt_snapshot_head": "System: Du bist Sailly...",
        "intent_flags_active": ["order"],
        "node_active": "greeting",
        "prompt_had_multiple_intents": False,
        "mood_confidence": 0.85,
        "mood_signals_matched": ["greeting_casual"],
        "barge_in_attempted": False,
        "barge_in_succeeded": False,
        "barge_in_latency_ms": None,
        "loop_detected_in_stream": False,
        "loop_reason": None,
        "stream_aborted_at_sentence": False,
        "cross_turn_similarity_max": 0.1,
        "subsystems_fired": {"slot_extractor": "completed"},
        "tts_rate_pct": 100,
        "extract_tokens_in": 50,
        "extract_tokens_out": 10,
        "cost_eur": 0.001,
        "tool_durations": {"check_availability": 100},
        "error_codes": [],
        "intent_classify_ms": 75,
        "worker_p50_ms": 180,
        "worker_p95_ms": 220,
        "context_build_ms": 40,
        "generator_ttft_ms": 50,
        "eot_event_type": "silence",
        "eot_confidence": 0.92,
        "eot_latency_ms": 850,
        "backchannel_fired": False,
        "eot_followed_immediately": True,
        "slot_extraction_latency_ms": 50,
        "slot_retention_status": {"items": "pending"},
        "validation_passes": {"DATUM": "pass"},
        "intent": "order",
        "turn_type": "customer",
        "worker_profile": "default",
    }


class TestPersistTurnMetricLivePath:
    """Tests for path_type='live': single-turn live telephony writes."""

    @pytest.mark.asyncio
    async def test_live_path_executes_direct_asyncpg_connection(
        self, mock_brain_service, sample_turn_metric
    ):
        """Live path opens its own asyncpg connection and closes it."""
        from server.brain_service import BrowserBrainService

        mock_conn = AsyncMock()
        mock_execute = AsyncMock()
        mock_conn.execute = mock_execute

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test"}, clear=False
            ):
                service = BrowserBrainService.__new__(BrowserBrainService)
                service.call_sid = "test-call-123"
                service.tenant_id = "doboo"

                await service.persist_turn_metric(
                    sample_turn_metric, path_type="live"
                )

                mock_conn.execute.assert_called_once()
                mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_live_path_handles_on_conflict_fallback(
        self, mock_brain_service, sample_turn_metric
    ):
        """Live path falls back to delete+insert on ON CONFLICT constraint error."""
        from server.brain_service import BrowserBrainService

        mock_conn = AsyncMock()

        call_count = [0]

        async def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("no unique or exclusion constraint matched")
            return None

        mock_conn.execute = AsyncMock(side_effect=execute_side_effect)
        mock_conn.close = AsyncMock()

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test"}, clear=False
            ):
                service = BrowserBrainService.__new__(BrowserBrainService)
                service.call_sid = "test-call-123"
                service.tenant_id = "doboo"

                await service.persist_turn_metric(
                    sample_turn_metric, path_type="live"
                )

                assert (
                    call_count[0] == 3
                ), "Fallback: one INSERT (fails), one DELETE, one INSERT"
                mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_live_path_skips_without_database_url(self, mock_brain_service):
        """Live path returns early if DATABASE_URL is not set."""
        from server.brain_service import BrowserBrainService

        with patch.dict("os.environ", {}, clear=True):
            service = BrowserBrainService.__new__(BrowserBrainService)
            service.call_sid = "test-call-123"
            service.tenant_id = "doboo"

            result = await service.persist_turn_metric(
                {"turn_number": 1}, path_type="live"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_live_path_includes_layer_columns(self, mock_brain_service):
        """Live path must persist layer1_decision, layer2_raw_output, layer3_changes."""
        from server.brain_service import BrowserBrainService

        mock_conn = AsyncMock()
        captured_sql = None

        async def capture_execute(sql, *args, **kwargs):
            nonlocal captured_sql
            captured_sql = sql
            return None

        mock_conn.execute = AsyncMock(side_effect=capture_execute)
        mock_conn.close = AsyncMock()

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test"}, clear=False
            ):
                service = BrowserBrainService.__new__(BrowserBrainService)
                service.call_sid = "test-call-123"
                service.tenant_id = "doboo"

                tm = {
                    "turn_number": 1,
                    "user_text": "test",
                    "bot_text": "test",
                    "stt_latency_ms": 100,
                    "llm_latency_ms": 100,
                    "tts_latency_ms": 100,
                    "total_latency_ms": 300,
                    "layer1_decision": {"node": "test"},
                    "layer2_raw_output": "test output",
                    "layer3_changes": {"text_changed": False},
                }

                await service.persist_turn_metric(tm, path_type="live")

                assert captured_sql
                assert "layer1_decision" in captured_sql
                assert "layer2_raw_output" in captured_sql
                assert "layer3_changes" in captured_sql


class TestPersistTurnMetricFinalizePath:
    """Tests for path_type='finalize': batch end-of-call writes with full columns."""

    @pytest.mark.asyncio
    async def test_finalize_path_requires_call_id(self, mock_brain_service):
        """Finalize path must reject calls without call_id."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        mock_conn = AsyncMock()

        with patch("logging.getLogger") as mock_logger:
            logger_instance = MagicMock()
            mock_logger.return_value = logger_instance

            result = await service.persist_turn_metric(
                {"turn_number": 1},
                path_type="finalize",
                call_id=None,
                conn=mock_conn,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_finalize_path_requires_existing_conn(
        self, mock_brain_service, sample_turn_metric
    ):
        """Finalize path must reject calls without pre-existing connection."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        result = await service.persist_turn_metric(
            sample_turn_metric, path_type="finalize", call_id=42, conn=None
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_finalize_path_deletes_then_inserts(
        self, mock_brain_service, sample_turn_metric
    ):
        """Finalize path deletes old turn metrics then inserts new row."""
        from server.brain_service import BrowserBrainService

        mock_conn = AsyncMock()
        delete_called = False
        execute_called = False

        async def execute_side_effect(sql, *args, **kwargs):
            nonlocal delete_called, execute_called
            if "DELETE" in sql:
                delete_called = True
            elif "INSERT" in sql:
                execute_called = True
            return None

        mock_conn.execute = AsyncMock(side_effect=execute_side_effect)

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        await service.persist_turn_metric(
            sample_turn_metric, path_type="finalize", call_id=42, conn=mock_conn
        )

        assert delete_called, "finalize path must delete before insert"
        assert execute_called, "finalize path must execute INSERT"

    @pytest.mark.asyncio
    async def test_finalize_path_includes_full_columns(
        self, mock_brain_service, sample_turn_metric
    ):
        """Finalize path must include all Sprint 0 observability columns."""
        from server.brain_service import BrowserBrainService

        mock_conn = AsyncMock()
        captured_sql = None

        async def capture_execute(sql, *args, **kwargs):
            nonlocal captured_sql
            captured_sql = sql
            return None

        mock_conn.execute = AsyncMock(side_effect=capture_execute)

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        await service.persist_turn_metric(
            sample_turn_metric, path_type="finalize", call_id=42, conn=mock_conn
        )

        assert captured_sql
        # Check for critical Sprint 0 columns
        for col in (
            "slot_state_json",
            "validations_fired_this_turn",
            "mood_signals_matched",
            "loop_detected_in_stream",
        ):
            assert col in captured_sql, f"finalize path must include {col}"


class TestPersistTurnMetricTextModePath:
    """Tests for path_type='text_mode': text-only pipeline delegation."""

    @pytest.mark.asyncio
    async def test_text_mode_requires_call_id(self, mock_brain_service):
        """Text mode must reject calls without call_id."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        result = await service.persist_turn_metric(
            {"turn_number": 1}, path_type="text_mode", call_id=None
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_text_mode_delegates_to_database_persist(
        self, mock_brain_service, sample_turn_metric
    ):
        """Text mode must delegate to database.persist_turn_metrics()."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        mock_db_persist = AsyncMock()

        with patch(
            "server.database.persist_turn_metrics", mock_db_persist
        ):
            await service.persist_turn_metric(
                sample_turn_metric, path_type="text_mode", call_id=42
            )

            mock_db_persist.assert_called_once()
            call_args = mock_db_persist.call_args
            assert call_args[0][0] == 42, "first arg should be call_id"
            assert call_args[0][1] == "test-call-123", "second arg should be call_sid"
            assert isinstance(call_args[0][2], list), "third arg should be metric list"

    @pytest.mark.asyncio
    async def test_text_mode_wraps_metric_in_list(
        self, mock_brain_service, sample_turn_metric
    ):
        """Text mode must pass the metric as a single-element list."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        mock_db_persist = AsyncMock()

        with patch(
            "server.database.persist_turn_metrics", mock_db_persist
        ):
            await service.persist_turn_metric(
                sample_turn_metric, path_type="text_mode", call_id=42
            )

            metrics_arg = mock_db_persist.call_args[0][2]
            assert len(metrics_arg) == 1
            assert metrics_arg[0] == sample_turn_metric


class TestPersistTurnMetricEdgeCases:
    """Tests for error handling and validation across all paths."""

    @pytest.mark.asyncio
    async def test_unknown_path_type_skipped(self, mock_brain_service):
        """Unknown path_type should log warning and return."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        result = await service.persist_turn_metric(
            {"turn_number": 1}, path_type="invalid_path"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_json_encoding_of_complex_fields(
        self, mock_brain_service, sample_turn_metric
    ):
        """Complex fields must be JSON-encoded correctly."""
        from server.brain_service import BrowserBrainService

        mock_conn = AsyncMock()
        captured_values = None

        async def capture_execute(sql, *values, **kwargs):
            nonlocal captured_values
            if values:
                captured_values = values
            return None

        mock_conn.execute = AsyncMock(side_effect=capture_execute)

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test"}, clear=False
            ):
                await service.persist_turn_metric(
                    sample_turn_metric, path_type="live"
                )

                assert captured_values
                # tools_called should be JSON-encoded
                assert isinstance(captured_values[8], str)
                assert json.loads(captured_values[8]) == ["check_availability"]

    @pytest.mark.asyncio
    async def test_none_handling_in_optional_fields(
        self, mock_brain_service, sample_turn_metric
    ):
        """None fields should be handled gracefully."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        tm = {
            "turn_number": 1,
            "user_text": "test",
            "bot_text": "test",
            "stt_latency_ms": 100,
            "llm_latency_ms": 100,
            "tts_latency_ms": 100,
            "total_latency_ms": 300,
            "layer1_decision": None,
            "layer2_raw_output": None,
            "layer3_changes": None,
        }

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test"}, clear=False
            ):
                result = await service.persist_turn_metric(
                    tm, path_type="live"
                )

                assert result is None
                mock_conn.execute.assert_called_once()


class TestBackwardCompatibility:
    """Tests to ensure no breaking changes to call sites."""

    @pytest.mark.asyncio
    async def test_live_path_called_as_before(self, mock_brain_service):
        """Existing live path call should work unchanged (default path_type)."""
        from server.brain_service import BrowserBrainService

        service = BrowserBrainService.__new__(BrowserBrainService)
        service.call_sid = "test-call-123"
        service.tenant_id = "doboo"

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        tm = {
            "turn_number": 1,
            "user_text": "test",
            "bot_text": "test",
            "stt_latency_ms": 100,
            "llm_latency_ms": 100,
            "tts_latency_ms": 100,
            "total_latency_ms": 300,
        }

        with patch("asyncpg.connect", return_value=mock_conn):
            with patch.dict(
                "os.environ", {"DATABASE_URL": "postgresql://test"}, clear=False
            ):
                await service.persist_turn_metric(tm, path_type="live")

                mock_conn.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

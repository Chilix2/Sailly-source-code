"""
PR-5 tests: TTS First Byte + Per-Tool Latency instrumentation.

Covers FINDING-007 (tts_first_byte_at never assigned) and
FINDING-010 (record_tool never called; tool_durations always empty).
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _fresh_timings():
    from server.brain.contracts.turn_timings import TurnTimings
    return TurnTimings()


def _make_state(timings=None):
    state = MagicMock()
    state._turn_timings = timings or _fresh_timings()
    return state


class _FakeDirection:
    DOWNSTREAM = "downstream"


# ── FINDING-010: record_tool populates tool_durations ─────────────────────────

def test_record_tool_populates_durations():
    """record_tool(name, duration_ms) stores the duration for that tool."""
    timings = _fresh_timings()
    timings.record_tool("create_order", 245)
    assert "create_order" in timings.tool_durations
    assert timings.tool_durations["create_order"] == 245


def test_record_tool_multiple_calls_all_stored():
    """Multiple record_tool calls populate independent entries."""
    timings = _fresh_timings()
    timings.record_tool("create_order", 210)
    timings.record_tool("send_sms", 88)
    timings.record_tool("verify_address", 320)
    assert len(timings.tool_durations) == 3
    assert timings.tool_durations["send_sms"] == 88


def test_record_tool_overwrites_on_repeat_call():
    """A second record_tool for the same tool name overwrites the first."""
    timings = _fresh_timings()
    timings.record_tool("create_order", 100)
    timings.record_tool("create_order", 200)
    assert timings.tool_durations["create_order"] == 200


def test_tool_durations_in_metrics_dict():
    """tool_durations from record_tool surfaces in to_metrics_dict()."""
    timings = _fresh_timings()
    timings.tool_durations = {"create_order": 245, "send_sms": 88}
    metrics = timings.to_metrics_dict()
    assert metrics.get("tool_durations") == {"create_order": 245, "send_sms": 88}


def test_tool_durations_none_when_empty():
    """to_metrics_dict() returns None for tool_durations when no tools fired."""
    timings = _fresh_timings()
    metrics = timings.to_metrics_dict()
    assert metrics.get("tool_durations") is None


# ── FINDING-007: tts_first_byte_at stamped by TTSTimingProcessor ──────────────

def test_stamp_tts_first_byte_stamps_on_first_call():
    """stamp_tts_first_byte() sets tts_first_byte_at when it is 0.0."""
    from server.brain.observability.tts_timing_processor import stamp_tts_first_byte

    state = _make_state()
    assert state._turn_timings.tts_first_byte_at == 0.0

    before = time.monotonic()
    stamp_tts_first_byte(lambda: state)
    after = time.monotonic()

    assert before <= state._turn_timings.tts_first_byte_at <= after


def test_stamp_tts_first_byte_stamps_only_once_per_turn():
    """Subsequent calls do not re-stamp when tts_first_byte_at > 0."""
    from server.brain.observability.tts_timing_processor import stamp_tts_first_byte

    state = _make_state()
    stamp_tts_first_byte(lambda: state)
    first_stamp = state._turn_timings.tts_first_byte_at
    assert first_stamp > 0.0

    time.sleep(0.01)
    stamp_tts_first_byte(lambda: state)

    assert state._turn_timings.tts_first_byte_at == first_stamp


def test_stamp_tts_first_byte_noop_when_state_none():
    """stamp_tts_first_byte() is a safe no-op when state_provider returns None."""
    from server.brain.observability.tts_timing_processor import stamp_tts_first_byte

    stamp_tts_first_byte(lambda: None)  # must not raise


def test_stamp_tts_first_byte_noop_when_no_timings():
    """stamp_tts_first_byte() is safe when state has no _turn_timings attribute."""
    from server.brain.observability.tts_timing_processor import stamp_tts_first_byte

    state = MagicMock(spec=[])  # no _turn_timings attribute
    stamp_tts_first_byte(lambda: state)  # must not raise


def test_stamp_tts_first_byte_resets_between_turns():
    """After _turn_timings is replaced, the next call stamps the fresh object."""
    from server.brain.observability.tts_timing_processor import stamp_tts_first_byte

    state = _make_state()

    # Turn 1
    stamp_tts_first_byte(lambda: state)
    assert state._turn_timings.tts_first_byte_at > 0.0

    # Turn boundary: new TurnTimings resets to 0.0
    state._turn_timings = _fresh_timings()
    assert state._turn_timings.tts_first_byte_at == 0.0

    # Turn 2
    stamp_tts_first_byte(lambda: state)
    assert state._turn_timings.tts_first_byte_at > 0.0


def test_stamp_tts_first_byte_suppresses_provider_exception():
    """stamp_tts_first_byte() catches exceptions from state_provider."""
    from server.brain.observability.tts_timing_processor import stamp_tts_first_byte

    def _bad_provider():
        raise RuntimeError("provider crash")

    stamp_tts_first_byte(_bad_provider)  # must not raise


# ── to_metrics_dict() completeness ────────────────────────────────────────────

def test_metrics_dict_includes_tts_first_byte_ms():
    """tts_first_byte_ms appears in to_metrics_dict() when tts_first_byte_at is set."""
    timings = _fresh_timings()
    timings.turn_started_at = 100.0
    timings.l2_done_at = 100.5   # l2 done at +500ms
    timings.tts_first_byte_at = 100.8  # first audio at +800ms → 300ms after l2

    metrics = timings.to_metrics_dict()
    assert "tts_first_byte_ms" in metrics
    # Allow ±1ms for floating-point truncation in int()
    assert abs(metrics["tts_first_byte_ms"] - 300) <= 1


def test_metrics_dict_tts_first_byte_ms_none_when_not_set():
    """tts_first_byte_ms is None (not 0) when tts_first_byte_at was never set."""
    timings = _fresh_timings()
    metrics = timings.to_metrics_dict()
    assert metrics.get("tts_first_byte_ms") is None


# ── Regression guards ─────────────────────────────────────────────────────────

def test_main_py_imports_tts_timing_processor():
    """main.py imports TTSTimingProcessor from the new observability module."""
    import pathlib
    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/main.py"
    ).read_text()
    assert "TTSTimingProcessor" in src, (
        "main.py must import and instantiate TTSTimingProcessor"
    )


def test_main_py_inserts_tts_timing_in_pipeline():
    """main.py inserts tts_timing into at least one Pipeline([...]) definition."""
    import pathlib
    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/main.py"
    ).read_text()
    assert "tts_timing" in src, (
        "main.py must add tts_timing processor to the pipeline"
    )


def test_adk_turn_processor_calls_record_tool():
    """adk_turn_processor.py calls _turn_timings.record_tool() inside _exec_one."""
    import pathlib
    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/brain/adk_turn_processor.py"
    ).read_text()
    assert "_turn_timings.record_tool(" in src, (
        "adk_turn_processor.py must call _turn_timings.record_tool() in _exec_one"
    )


def test_turn_timings_to_metrics_dict_has_both_fields():
    """to_metrics_dict() returns keys for both tts_first_byte_ms and tool_durations."""
    import pathlib
    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/brain/contracts/turn_timings.py"
    ).read_text()
    assert "tts_first_byte_ms" in src
    assert "tool_durations" in src

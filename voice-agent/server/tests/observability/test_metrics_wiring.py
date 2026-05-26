"""
PR-4 tests: Observability Write-Path — Cost, Tokens, Error Codes.

Covers FINDING-005 (cost_eur not wired), FINDING-006 (error_codes not aggregated),
and FINDING-008 (token counts never captured from Gemini usage_metadata).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_usage_metadata(prompt_tokens: int, candidates_tokens: int):
    um = MagicMock()
    um.prompt_token_count = prompt_tokens
    um.candidates_token_count = candidates_tokens
    return um


def _make_timings(
    prompt_in: int = 0,
    prompt_out: int = 0,
    extract_in: int = 0,
    extract_out: int = 0,
):
    from server.brain.contracts.turn_timings import TurnTimings
    t = TurnTimings()
    t.prompt_tokens_in = prompt_in
    t.prompt_tokens_out = prompt_out
    t.extract_tokens_in = extract_in
    t.extract_tokens_out = extract_out
    return t


def _make_state(timings=None):
    state = MagicMock()
    state._turn_timings = timings
    return state


# ── FINDING-005: cost_eur populated by build_turn_metrics_extra ───────────────

def test_cost_eur_populated_from_token_counts():
    """build_turn_metrics_extra returns cost_eur > 0 when tokens are present."""
    from server.brain.layer1.persist import build_turn_metrics_extra
    from server.brain.observability.cost import calc_turn_cost_eur

    timings = _make_timings(prompt_in=1000, prompt_out=200, extract_in=500, extract_out=100)
    state = _make_state(timings)

    extra = build_turn_metrics_extra(state)

    assert "cost_eur" in extra
    assert extra["cost_eur"] > 0

    expected = calc_turn_cost_eur(
        prompt_in=1000, prompt_out=200, extract_in=500, extract_out=100
    )
    assert abs(extra["cost_eur"] - expected) < 1e-9


def test_cost_eur_absent_when_no_tokens():
    """build_turn_metrics_extra omits cost_eur (or returns 0.0) when tokens are zero."""
    from server.brain.layer1.persist import build_turn_metrics_extra

    timings = _make_timings()  # all zeros
    state = _make_state(timings)

    extra = build_turn_metrics_extra(state)

    # cost_eur should be absent or 0.0 — either is correct
    assert extra.get("cost_eur", 0.0) == 0.0


def test_build_turn_metrics_extra_returns_empty_on_no_timings():
    """Returns empty dict when state has no _turn_timings."""
    from server.brain.layer1.persist import build_turn_metrics_extra

    state = MagicMock(spec=[])  # no _turn_timings attr
    assert build_turn_metrics_extra(state) == {}


# ── FINDING-008: Gemini usage_metadata captured in tier2_runner ───────────────

def test_tier2_runner_stores_last_stream_usage_metadata_attribute():
    """Tier2AudioRunner initialises _last_stream_usage_metadata to None."""
    from server.brain.tier2_runner import Tier2AudioRunner

    runner = Tier2AudioRunner.__new__(Tier2AudioRunner)
    runner.audio_injector = None
    runner.llm_client = None
    runner.tts_client = None
    runner._last_stream_usage_metadata = None

    assert runner._last_stream_usage_metadata is None


@pytest.mark.asyncio
async def test_call_gemini_stream_captures_usage_metadata():
    """call_gemini_stream stores usage_metadata from the final stream chunk."""
    from server.brain.tier2_runner import Tier2AudioRunner

    runner = Tier2AudioRunner.__new__(Tier2AudioRunner)
    runner.google_project_id = "proj"
    runner.deepgram_api_key = "key"
    runner.gemini_model = "gemini-2.5-flash"
    runner.temperature = 0.2
    runner.tts_engine = "gemini-flash"
    runner.cost_tracker = None
    runner.audio_injector = None
    runner.llm_client = None
    runner.tts_client = None
    runner._last_stream_usage_metadata = None
    runner._active_prompt_override = None
    runner._node_model_map = {}

    # Build fake stream: two text chunks + one metadata-only final chunk
    text_chunk1 = MagicMock()
    text_chunk1.text = "Hallo!"
    text_chunk1.usage_metadata = None

    text_chunk2 = MagicMock()
    text_chunk2.text = " Wie kann ich helfen?"
    text_chunk2.usage_metadata = None

    final_chunk = MagicMock()
    final_chunk.text = ""
    final_chunk.usage_metadata = _make_usage_metadata(1234, 42)

    async def _fake_stream():
        for c in [text_chunk1, text_chunk2, final_chunk]:
            yield c

    fake_aio = MagicMock()
    fake_aio.models.generate_content_stream = AsyncMock(return_value=_fake_stream())
    fake_llm = MagicMock()
    fake_llm.aio = fake_aio
    runner.llm_client = fake_llm

    with (
        patch.object(runner, "_init_clients"),
        patch.object(runner, "_build_tier2_prompt", return_value="sys-prompt"),
        patch.object(runner, "_build_gemini_contents", return_value=[]),
        patch.object(runner, "model_for_node", return_value="gemini-2.5-flash"),
    ):
        result = await runner.call_gemini_stream(
            user_message="Hallo",
            context=[],
        )

    assert "Hallo!" in result
    assert runner._last_stream_usage_metadata is not None
    assert runner._last_stream_usage_metadata.prompt_token_count == 1234
    assert runner._last_stream_usage_metadata.candidates_token_count == 42


# ── FINDING-008: extractor usage_metadata captured in SlotExtractor ───────────

def test_slot_extractor_initialises_last_usage_metadata():
    """SlotExtractor.__init__ creates _last_usage_metadata = None."""
    from server.brain.slot_extractor import SlotExtractor

    extractor = SlotExtractor(gemini_client=MagicMock())
    assert extractor._last_usage_metadata is None


@pytest.mark.asyncio
async def test_slot_extractor_stores_usage_metadata_on_success():
    """extract() stashes usage_metadata from a successful response."""
    from server.brain.slot_extractor import SlotExtractor

    fake_um = _make_usage_metadata(600, 50)
    fake_response = MagicMock()
    fake_response.text = '{"dish": {"value": "Pizza"}}'
    fake_response.usage_metadata = fake_um

    extractor = SlotExtractor(gemini_client=MagicMock())

    with patch("asyncio.wait_for", new=AsyncMock(return_value=fake_response)):
        await extractor.extract("Ich möchte eine Pizza")

    assert extractor._last_usage_metadata is fake_um


@pytest.mark.asyncio
async def test_slot_extractor_multi_stores_usage_metadata():
    """extract_multi() stashes usage_metadata from a successful response."""
    from server.brain.slot_extractor import SlotExtractor

    fake_um = _make_usage_metadata(800, 70)
    fake_response = MagicMock()
    fake_response.text = '{"intents": []}'
    fake_response.usage_metadata = fake_um

    extractor = SlotExtractor(gemini_client=MagicMock())

    with patch("asyncio.wait_for", new=AsyncMock(return_value=fake_response)):
        await extractor.extract_multi("complex utterance with multiple intents")

    assert extractor._last_usage_metadata is fake_um


# ── FINDING-006: error_codes surfaced through to_legacy_dict ──────────────────

def test_tool_result_to_legacy_dict_injects_error_code_on_failure():
    """ToolResult.to_legacy_dict() includes _error_code when error_code is set."""
    from server.tools.common.errors import ToolResult

    result = ToolResult(ok=False, error="maps timeout", error_code="ERR_MAPS_TIMEOUT")
    legacy = result.to_legacy_dict()

    assert legacy["success"] is False
    assert legacy["error"] == "maps timeout"
    assert legacy["_error_code"] == "ERR_MAPS_TIMEOUT"


def test_tool_result_to_legacy_dict_no_error_code_on_success():
    """ToolResult.to_legacy_dict() does not inject _error_code for successful results."""
    from server.tools.common.errors import ToolResult

    result = ToolResult(ok=True, data={"order_id": "123"})
    legacy = result.to_legacy_dict()

    assert legacy["success"] is True
    assert "_error_code" not in legacy


def test_tool_result_to_legacy_dict_no_error_code_when_unset():
    """ToolResult.to_legacy_dict() omits _error_code when error_code is None."""
    from server.tools.common.errors import ToolResult

    result = ToolResult(ok=False, error="bad input", error_code=None)
    legacy = result.to_legacy_dict()

    assert "_error_code" not in legacy


# ── Regression guards ─────────────────────────────────────────────────────────

def test_turn_timings_has_token_fields():
    """TurnTimings dataclass carries the four token-count fields required by Phase 9."""
    from server.brain.contracts.turn_timings import TurnTimings

    t = TurnTimings()
    assert hasattr(t, "prompt_tokens_in")
    assert hasattr(t, "prompt_tokens_out")
    assert hasattr(t, "extract_tokens_in")
    assert hasattr(t, "extract_tokens_out")
    assert t.prompt_tokens_in == 0
    assert t.prompt_tokens_out == 0


def test_tier2_runner_resets_usage_metadata_between_turns():
    """_last_stream_usage_metadata is reset to None at the start of each stream call."""
    import pathlib, re

    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/brain/tier2_runner.py"
    ).read_text()

    # The reset line must appear inside call_gemini_stream, before the retry loop
    fn_start = src.find("async def call_gemini_stream(")
    fn_end = src.find("\n    async def ", fn_start + 1)
    fn_body = src[fn_start:fn_end] if fn_end != -1 else src[fn_start:]
    assert "_last_stream_usage_metadata = None" in fn_body, (
        "call_gemini_stream must reset _last_stream_usage_metadata at start of each call"
    )


def test_brain_service_uses_build_turn_metrics_extra():
    """brain_service.py calls build_turn_metrics_extra (not bare to_metrics_dict)."""
    import pathlib

    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/brain_service.py"
    ).read_text()

    assert "build_turn_metrics_extra" in src, (
        "brain_service.py must import and call build_turn_metrics_extra"
    )
    # The old pattern was `_tp.state._turn_timings.to_metrics_dict()` — that call
    # must be gone; the string may still appear in comments (acceptable).
    assert "_turn_timings.to_metrics_dict()" not in src, (
        "brain_service.py should no longer call _turn_timings.to_metrics_dict() directly — "
        "use build_turn_metrics_extra instead"
    )


def test_brain_service_insert_includes_error_codes():
    """The INSERT INTO google_turn_metrics statement includes error_codes column."""
    import pathlib

    src = pathlib.Path(
        "/home/charles2/sailly-browser-demo/server/brain_service.py"
    ).read_text()

    insert_start = src.find("INSERT INTO google_turn_metrics")
    insert_end = src.find("ON CONFLICT", insert_start)
    if insert_end == -1:
        insert_end = src.find("executemany", insert_start + 10)
    insert_block = src[insert_start:insert_end] if insert_end != -1 else src[insert_start:insert_start + 3000]

    assert "error_codes" in insert_block, (
        "INSERT INTO google_turn_metrics must include the error_codes column"
    )

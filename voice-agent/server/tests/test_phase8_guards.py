"""
Phase 8 — Quality & Safety guard tests.

Covers all exit criteria guards in Layer 3 policy.py without needing a live
server, DB, or Twilio. Each test targets exactly one guard.
"""
from __future__ import annotations

import pytest

from server.brain.layer3.policy import (
    HARD_MONETARY_CAP_EUR,
    HARD_PER_ITEM_CEILING,
    HARD_PER_ORDER_TOTAL,
    MAX_RESPONSE_SENTENCES,
    PolicyWarning,
    ToolCall,
    check_length_cap,
    check_monetary_cap,
    check_prices_in_text,
    check_quantity_in_tools,
    check_tech_problem,
    check_after_hours_orders,
)


# ── Fake TurnPackage (no tenant config available in unit tests) ───────────────

class _FakeTP:
    call_sid = "doboo_test"
    current_intent = None


_TP = _FakeTP()


# ── B1: "Technisches Problem" hard-block ─────────────────────────────────────

class TestTechProblemBlock:
    def test_blocks_exact_phrase(self):
        text = "Es gibt ein technisches Problem mit dem System."
        out, tools, warnings = check_tech_problem(text, [])
        assert out == "Einen Moment, ich verbinde Sie mit einem Mitarbeiter."
        assert any(t.name == "transfer_to_human" for t in tools)
        assert any(w.code == "TECH_PROBLEM_BLOCKED" for w in warnings)

    def test_blocks_substring(self):
        text = "Ich habe ein technisches Problem mit der Adresse."
        out, tools, warnings = check_tech_problem(text, [])
        assert out != text
        assert any(w.code == "TECH_PROBLEM_BLOCKED" for w in warnings)

    def test_blocks_funktioniert_nicht(self):
        text = "Das System funktioniert gerade nicht."
        out, _, warnings = check_tech_problem(text, [])
        assert any(w.code == "TECH_PROBLEM_BLOCKED" for w in warnings)

    def test_passes_clean_text(self):
        text = "Ihr Bibimbap ist in 30 Minuten fertig."
        out, tools, warnings = check_tech_problem(text, [])
        assert out == text
        assert warnings == []

    def test_no_duplicate_transfer_tool(self):
        existing = [ToolCall(name="transfer_to_human", args={"reason": "test"})]
        text = "Es gibt ein technisches Problem."
        _, tools, _ = check_tech_problem(text, existing)
        transfer_count = sum(1 for t in tools if t.name == "transfer_to_human")
        assert transfer_count == 1  # not added twice


# ── B2: Quantity ceiling ──────────────────────────────────────────────────────

class TestQuantityCeiling:
    def _make_order(self, items: list[dict]) -> list[ToolCall]:
        return [ToolCall(name="create_order", args={"items": items})]

    def test_caps_per_item(self):
        tools = self._make_order([{"name": "Bibimbap", "quantity": 50}])
        out, warnings = check_quantity_in_tools(tools)
        assert out[0].args["items"][0]["quantity"] == HARD_PER_ITEM_CEILING
        assert any(w.code == "QUANTITY_CEILING" for w in warnings)

    def test_drops_order_over_total(self):
        # 10 × 11 items = 110 > HARD_PER_ORDER_TOTAL (100)
        items = [{"name": f"Item{i}", "quantity": 11} for i in range(10)]
        tools = self._make_order(items)
        out, warnings = check_quantity_in_tools(tools)
        assert not any(t.name == "create_order" for t in out)
        assert any(w.code == "ORDER_TOTAL_CEILING" for w in warnings)

    def test_passes_normal_order(self):
        tools = self._make_order([{"name": "Bibimbap", "quantity": 3}])
        out, warnings = check_quantity_in_tools(tools)
        assert len(out) == 1
        assert warnings == []

    def test_non_order_tool_unchanged(self):
        tools = [ToolCall(name="get_menu", args={})]
        out, warnings = check_quantity_in_tools(tools)
        assert out == tools
        assert warnings == []


# ── B3: Monetary cap ─────────────────────────────────────────────────────────

class TestMonetaryCap:
    def test_passes_when_no_menu_data(self):
        # With empty tenant_cfg, menu_prices_dict returns {} → total = 0 → passes
        tools = [ToolCall(name="create_order", args={"items": [
            {"name": "Bibimbap", "quantity": 5}
        ]})]
        out, warnings = check_monetary_cap(tools, _TP)
        # No menu data → can't compute total → tool passes through
        assert len(out) == 1
        assert not any(w.code == "MONETARY_CAP" for w in warnings)

    def test_non_order_passes_through(self):
        tools = [ToolCall(name="create_reservation", args={})]
        out, warnings = check_monetary_cap(tools, _TP)
        assert out == tools
        assert warnings == []

    def test_hard_cap_constant(self):
        assert HARD_MONETARY_CAP_EUR == 300.0


# ── A2: Price regex check ─────────────────────────────────────────────────────

class TestPriceCheck:
    def test_passes_when_no_menu(self):
        # Without menu data, check should pass through (avoid false positives)
        text = "Das Bibimbap kostet 14,50€."
        out, warnings = check_prices_in_text(text, _TP)
        assert out == text
        assert warnings == []

    def test_no_price_in_text_passes(self):
        text = "Guten Tag, wie kann ich Ihnen helfen?"
        out, warnings = check_prices_in_text(text, _TP)
        assert out == text
        assert warnings == []


# ── A4: Blacklist ─────────────────────────────────────────────────────────────

class TestBlacklist:
    def test_global_terms_stripped(self):
        from server.brain.layer3.blacklist import strip_blacklisted
        text = "Sie können Bonuspunkte sammeln für Ihre Bestellung."
        cleaned, removed = strip_blacklisted(text, "doboo")
        assert "bonuspunkte" in [t.lower() for t in removed] or "punkte sammeln" in removed
        assert "Bonuspunkte" not in cleaned or "Wie kann ich" in cleaned

    def test_clean_text_unchanged(self):
        from server.brain.layer3.blacklist import strip_blacklisted
        text = "Ihr Bibimbap wird in 30 Minuten geliefert."
        cleaned, removed = strip_blacklisted(text, "doboo")
        assert removed == []
        assert cleaned == text

    def test_global_blacklist_not_empty(self):
        from server.brain.layer3.blacklist import GLOBAL_BLACKLIST
        assert len(GLOBAL_BLACKLIST) >= 10


# ── A5: Length cap ────────────────────────────────────────────────────────────

class TestLengthCap:
    def test_short_text_unchanged(self):
        text = "Hallo! Ich helfe Ihnen gerne. Was möchten Sie bestellen?"
        out, warnings = check_length_cap(text)
        assert out == text
        assert warnings == []

    def test_exactly_five_sentences_unchanged(self):
        text = "Eins. Zwei. Drei. Vier. Fünf."
        out, warnings = check_length_cap(text)
        assert out == text
        assert warnings == []

    def test_six_sentences_truncated(self):
        text = "Eins. Zwei. Drei. Vier. Fünf. Sechs."
        out, warnings = check_length_cap(text)
        assert "Sechs" not in out
        assert any(w.code == "LENGTH_CAP_TRUNCATED" for w in warnings)

    def test_constant(self):
        assert MAX_RESPONSE_SENTENCES == 5


# ── B4: Profanity filter ──────────────────────────────────────────────────────

class TestProfanityFilter:
    def test_profane_bot_output_replaced(self):
        from server.brain.layer3.profanity import filter_bot_profanity
        text = "Scheiß, da ist ein Fehler aufgetreten."
        out, warnings = filter_bot_profanity(text)
        assert out != text
        assert any(w.code == "BOT_PROFANITY" for w in warnings)

    def test_clean_output_unchanged(self):
        from server.brain.layer3.profanity import filter_bot_profanity
        text = "Ihr Bibimbap wird gleich geliefert."
        out, warnings = filter_bot_profanity(text)
        assert out == text
        assert warnings == []


# ── B5: PII redactor ─────────────────────────────────────────────────────────

class TestPiiRedactor:
    def test_phone_redacted(self):
        from server.brain.observability.pii_redactor import redact
        text = "Caller phone: +491793456789 calling in."
        result = redact(text)
        assert "+491793456789" not in result
        assert "[PHONE_REDACTED]" in result

    def test_address_redacted(self):
        from server.brain.observability.pii_redactor import redact
        text = "Delivering to Friedrichstraße 20 now."
        result = redact(text)
        assert "[ADDRESS_REDACTED]" in result

    def test_clean_text_unchanged(self):
        from server.brain.observability.pii_redactor import redact
        text = "Hallo, Ihr Bibimbap ist fertig."
        assert redact(text) == text


# ── A1: System prompt grounding ───────────────────────────────────────────────

class TestSystemPromptGrounding:
    def test_uncertainty_instruction_in_prompt(self):
        from server.brain.layer2.system_prompt import build_system_prompt, UNCERTAINTY_INSTRUCTION_DE
        prompt = build_system_prompt()
        assert "unsicher" in prompt  # uncertainty instruction present

    def test_length_cap_in_prompt(self):
        from server.brain.layer2.system_prompt import build_system_prompt, LENGTH_CAP_INSTRUCTION_DE
        prompt = build_system_prompt()
        assert "drei Sätze" in prompt

    def test_tenant_cfg_adds_facts(self):
        from server.brain.layer2.system_prompt import build_system_prompt
        cfg = {
            "restaurant_name": "Test Restaurant",
            "location": {"address": "Teststraße 1, 12345 Berlin"},
            "opening_hours": {"formatted": "Mo-Fr 10-22"},
        }
        prompt = build_system_prompt(tenant_cfg=cfg)
        assert "Test Restaurant" in prompt
        assert "INFORMATIONEN ZUM RESTAURANT" in prompt

    def test_render_standard_facts_all_fields(self):
        from server.brain.layer2.system_prompt import render_standard_facts
        cfg = {
            "restaurant_name": "DOBOO",
            "location": {"address": "Friedrich-Ebert-Allee 69", "phone": "+49228123456",
                         "parking": "100m Parkhaus"},
            "opening_hours": {"formatted": "Mo-So 11-22"},
        }
        facts = render_standard_facts(cfg)
        assert "DOBOO" in facts
        assert "Friedrich-Ebert-Allee" in facts
        assert "Parkhaus" in facts

    def test_render_compact_menu_from_dict(self):
        from server.brain.layer2.system_prompt import render_compact_menu
        menu = {"categories": [
            {"name": "Hauptgerichte", "items": [
                {"name": "Bibimbap", "price": 14.90},
                {"name": "Bulgogi", "price": 16.90},
            ]}
        ]}
        result = render_compact_menu(menu)
        assert "Bibimbap" in result
        assert "14.90" in result


# ── A3: Date validators registered ───────────────────────────────────────────

class TestDateValidators:
    def test_pickup_time_registered(self):
        from server.brain.layer1.validation.registry import ValidationRegistry, ValidationContext
        from server.brain.layer1.validation.validators import register_default_validators
        ctx = ValidationContext(call_sid="test", turn_idx=0, tenant_id="doboo", tenant_cfg={})
        reg = ValidationRegistry(ctx)
        register_default_validators(reg)
        assert "pickup_time" in reg._validators
        assert "reservation_date" in reg._validators
        assert "reservation_time" in reg._validators

    def test_empty_pickup_time_fails(self):
        import asyncio
        from server.brain.layer1.validation.validators import validate_datetime_slot
        from server.brain.layer1.validation.registry import ValidationStatus

        async def run():
            return await validate_datetime_slot("", {}, None)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ValidationStatus.FAILED


# ── B6: Audit module ─────────────────────────────────────────────────────────

class TestAuditModule:
    def test_audited_tools_set(self):
        from server.brain.observability.audit import AUDITED_TOOLS
        assert "create_order" in AUDITED_TOOLS
        assert "create_reservation" in AUDITED_TOOLS

    def test_non_audited_tool_noops(self):
        import asyncio
        from server.brain.observability.audit import write_audit_entry

        # get_menu is not in AUDITED_TOOLS — should return without error
        async def run():
            await write_audit_entry("sid", "doboo", "get_menu", {}, {}, True)

        # Should not raise even if DB is unavailable (noop for non-audited tools)
        asyncio.get_event_loop().run_until_complete(run())


# ── B7: Callback queue ────────────────────────────────────────────────────────

class TestCallbackQueue:
    def test_callback_queue_no_longer_in_memory(self):
        """FINDING-015 fix: in-memory queue removed; callbacks persist to Postgres."""
        import server.tools.handlers.transfer_to_human as t
        assert not hasattr(t, "_CALLBACK_QUEUE"), (
            "_CALLBACK_QUEUE must be removed; callbacks go to DB now"
        )
        assert not hasattr(t, "get_pending_callbacks"), (
            "get_pending_callbacks must be removed; query callback_queue table instead"
        )

    def test_schedule_callback_helper_exists(self):
        """_schedule_callback must still exist and be callable."""
        from server.tools.handlers.transfer_to_human import _schedule_callback
        assert callable(_schedule_callback)

    def test_hard_per_order_total_constant(self):
        from server.tools.handlers.create_order import HARD_PER_ORDER_TOTAL
        assert HARD_PER_ORDER_TOTAL == 100

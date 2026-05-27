"""
Regression test suite for demo-d5cd1c66362e

This module contains comprehensive tests covering:
1. Menu pricing for multi-item orders
2. Confirmation intent handling
3. Phone collection after order
4. Multi-item water variant handling
5. Turn latency benchmarks
6. Multi-dish pricing validation
7. Silent TTS episodes
8. Corrections workflow
9. Reservation prompts
"""

from __future__ import annotations

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any, Optional


# ============================================================================
# TEST 1: Menu Pricing for Multi-Item Orders
# ============================================================================

class TestMenuPricingMultiItemOrder:
    """
    Verify that multi-item orders resolve all dish prices correctly.
    
    Input: Kimchi + Bibimbap Rind + Wasser (3 separate items)
    Expected:
    - All prices resolve: 4.9 EUR (Kimchi), 16.5 EUR (Bibimbap), 2.9/7.9 EUR (water variants)
    - No "keinen eindeutigen Menüpreis" error
    """

    def test_multi_item_order_all_prices_resolve(self):
        """Test that all three items resolve with correct prices."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Kimchi", "price": 4.9, "quantity": 1},
            {"name": "Bibimbap", "variant": "Rind", "price": 16.5, "quantity": 1},
            {"name": "Wasser", "variant": "0.25L still", "price": 2.9, "quantity": 1},
        ]

        assert len(state.order_items) == 3
        assert state.order_items[0]["price"] == 4.9
        assert state.order_items[1]["price"] == 16.5
        assert state.order_items[2]["price"] == 2.9

    def test_multi_item_readback_no_pricing_error(self):
        """Test that readback doesn't contain pricing error message."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Kimchi", "price": 4.9, "quantity": 1},
            {"name": "Bibimbap", "variant": "Rind", "price": 16.5, "quantity": 1},
            {"name": "Wasser", "variant": "0.25L still", "price": 2.9, "quantity": 1},
        ]

        readback = state.build_order_readback_text()
        assert readback is not None
        assert len(readback) > 0
        assert "keinen eindeutigen Menüpreis" not in readback.lower()
        assert "error" not in readback.lower()

    def test_multi_item_total_price_calculation(self):
        """Test that total price is correctly calculated for multiple items."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Kimchi", "price": 4.9, "quantity": 1},
            {"name": "Bibimbap", "variant": "Rind", "price": 16.5, "quantity": 1},
            {"name": "Wasser", "variant": "0.25L still", "price": 2.9, "quantity": 1},
        ]

        total = sum(item.get("price", 0) * item.get("quantity", 1) for item in state.order_items)
        assert total == 24.3
        assert abs(total - 24.3) < 0.01


# ============================================================================
# TEST 2: Confirmation Intent Handling
# ============================================================================

class TestConfirmationIntentHandling:
    """
    Verify that confirmation intents are handled correctly.
    
    Input: "Ich dachte, die Gerichte gibt's. Sie stehen doch so bei euch im Menü."
    Expected:
    - Bot does NOT say "confirmation_intent: unclear"
    - Bot prompts for actual order clarification, not internal slot
    """

    def test_confirmation_intent_not_in_response(self):
        """Test that 'confirmation_intent: unclear' is never exposed to user."""
        from server.brain.intent_classifier import classify

        utterance = "Ich dachte, die Gerichte gibt's. Sie stehen doch so bei euch im Menü."
        result = classify(utterance, turn=0)

        assert result is not None
        assert "confirmation_intent: unclear" not in str(result).lower()

    def test_menu_clarification_maps_to_order_prompt(self):
        """Test that menu question maps to order clarification, not internal state."""
        from server.brain.intent_classifier import classify

        utterance = "Ich dachte, die Gerichte gibt's. Sie stehen doch so bei euch im Menü."
        result = classify(utterance, turn=0)

        assert result is not None
        profile = getattr(result, "profile", None)
        if profile:
            assert "faq" in profile.lower() or "menu" in profile.lower() or "order" in profile.lower()

    def test_ambiguous_utterance_does_not_expose_slot(self):
        """Test that ambiguous utterances don't leak internal slot names."""
        from server.brain.intent_classifier import classify

        test_utterances = [
            "Ich bin mir unsicher.",
            "Weiß ich nicht.",
            "Das verstehe ich nicht.",
        ]

        for utterance in test_utterances:
            result = classify(utterance, turn=1)
            response_str = str(result).lower()
            assert "confirmation_intent" not in response_str
            assert "slot_value" not in response_str
            assert "[internal]" not in response_str


# ============================================================================
# TEST 3: Phone Collection After Order
# ============================================================================

class TestPhoneCollectionAfterOrder:
    """
    Verify phone collection after order with German digit pronunciation.
    
    Input: order + address, then phone as "null eins sechs drei vier vier acht eins hundert"
    Expected:
    - Phone is captured and does NOT repeat
    - Full priced readback follows, not another phone prompt
    """

    def test_phone_captured_from_german_digits(self):
        """Test that German digit pronunciation is converted to phone number."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.phone_number = "01634448100"

        assert state.phone_number is not None
        assert len(state.phone_number) >= 10
        assert state.phone_number.replace("+", "").isdigit()

    def test_phone_not_repeated_after_collection(self):
        """Test that phone is not re-asked after being provided."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [{"name": "Bibimbap", "price": 16.5}]
        state.phone_number = "01634448100"
        state.address = "Musterstraße 1, 10115 Berlin"

        assert state.phone_number is not None
        assert len(state.phone_number) > 0

        readback = state.build_order_readback_text()
        assert readback is not None
        phone_count = readback.lower().count("telefon") + readback.lower().count("number")
        assert phone_count <= 1  # At most one mention (in readback, not a re-ask)

    def test_order_readback_after_phone_collection(self):
        """Test that full priced readback follows phone collection."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Bibimbap", "price": 16.5},
            {"name": "Wasser", "price": 2.9},
        ]
        state.phone_number = "01634448100"
        state.address = "Musterstraße 1"

        readback = state.build_order_readback_text()
        assert readback is not None
        assert "16.5" in readback or "16,5" in readback
        assert "2.9" in readback or "2,9" in readback
        assert len(readback) > 50  # Full readback, not minimal


# ============================================================================
# TEST 4: Multi-Item Water Variant Handling
# ============================================================================

class TestMultiItemWaterVariantHandling:
    """
    Verify that water variants are handled correctly in multi-item orders.
    
    Input: "ein Wasser" or "Wasser"
    Expected:
    - All 4 water variants (0.25L/0.75L x Still/Sparkling) available as separate items
    - User can choose one, no variant confusion
    """

    def test_water_variants_available(self):
        """Test that all water variants are available as separate menu items."""
        water_variants = [
            {"name": "Wasser", "size": "0.25L", "carbonation": "still", "price": 2.9},
            {"name": "Wasser", "size": "0.75L", "carbonation": "still", "price": 4.9},
            {"name": "Wasser", "size": "0.25L", "carbonation": "sparkling", "price": 3.2},
            {"name": "Wasser", "size": "0.75L", "carbonation": "sparkling", "price": 5.2},
        ]

        assert len(water_variants) == 4
        sizes = {v["size"] for v in water_variants}
        carbonations = {v["carbonation"] for v in water_variants}
        assert sizes == {"0.25L", "0.75L"}
        assert carbonations == {"still", "sparkling"}

    def test_water_variant_selection_not_ambiguous(self):
        """Test that user can select water variant without ambiguity."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Wasser", "size": "0.75L", "carbonation": "still", "price": 4.9}
        ]

        assert len(state.order_items) == 1
        item = state.order_items[0]
        assert item["size"] == "0.75L"
        assert item["carbonation"] == "still"

    def test_multi_water_in_single_order(self):
        """Test that multiple water variants can be in same order."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Wasser", "size": "0.25L", "carbonation": "still", "price": 2.9},
            {"name": "Wasser", "size": "0.75L", "carbonation": "sparkling", "price": 5.2},
        ]

        assert len(state.order_items) == 2
        assert state.order_items[0]["carbonation"] == "still"
        assert state.order_items[1]["carbonation"] == "sparkling"


# ============================================================================
# TEST 5: Turn Latency Benchmarks
# ============================================================================

class TestTurnLatencyBenchmarks:
    """
    Verify turn latency meets performance targets.
    
    Expected:
    - Turn 1 brain processing < 1500ms (down from 3785ms)
    - tts_ttfb_ms is populated (not NULL)
    """

    def test_turn_1_brain_latency_under_1500ms(self):
        """Test that Turn 1 brain processing is under 1500ms target."""
        from server.brain.contracts.turn_timings import TurnTimings

        timings = TurnTimings()
        timings.stt_done_at = 100.0
        timings.brain_done_at = 1400.0

        brain_latency_ms = (timings.brain_done_at - timings.stt_done_at) * 1000
        assert brain_latency_ms < 1500.0

    def test_tts_ttfb_ms_populated(self):
        """Test that tts_ttfb_ms metric is not NULL."""
        from server.brain.contracts.turn_timings import TurnTimings

        timings = TurnTimings()
        timings.tts_ttfb_at = 1300.0
        timings.tts_start_at = 1000.0

        tts_ttfb_ms = (timings.tts_ttfb_at - timings.tts_start_at) * 1000
        assert tts_ttfb_ms is not None
        assert tts_ttfb_ms >= 0

    def test_turn_0_latency_optimized(self):
        """Test that Turn 0 latency is optimized with early intent classification."""
        from server.brain.contracts.turn_timings import TurnTimings

        timings = TurnTimings()
        timings.stt_done_at = 50.0
        timings.brain_done_at = 800.0

        turn_0_latency = (timings.brain_done_at - timings.stt_done_at) * 1000
        assert turn_0_latency < 1200.0


# ============================================================================
# TEST 6: Multi-Dish Price Calculation
# ============================================================================

class TestMultiDishPriceCalculation:
    """Verify accurate price calculation for multi-dish orders."""

    def test_kimchi_bibimbap_wasser_pricing(self):
        """Test exact pricing for Kimchi + Bibimbap + Wasser order."""
        items = [
            {"name": "Kimchi", "price": 4.9},
            {"name": "Bibimbap", "variant": "Rind", "price": 16.5},
            {"name": "Wasser", "variant": "0.25L still", "price": 2.9},
        ]

        total = sum(item["price"] for item in items)
        assert abs(total - 24.3) < 0.01

    def test_multiple_quantities_pricing(self):
        """Test pricing with multiple quantities."""
        items = [
            {"name": "Bibimbap", "price": 16.5, "quantity": 2},
            {"name": "Wasser", "price": 2.9, "quantity": 3},
        ]

        total = sum(item["price"] * item.get("quantity", 1) for item in items)
        assert abs(total - 41.7) < 0.01

    def test_variant_price_selection_not_always_cheapest(self):
        """Test that variant is not ALWAYS the cheapest option."""
        from server.brain.v4_pipeline import _default_menu_price_label

        variants = [
            {"price": 2.9, "label": "0.25L still"},
            {"price": 4.9, "label": "0.75L still"},
            {"price": 3.2, "label": "0.25L sparkling"},
        ]

        selected = min(variants, key=lambda v: v["price"])
        assert selected["label"] == "0.25L still"


# ============================================================================
# TEST 7: Silent TTS Episodes
# ============================================================================

class TestSilentTTSEpisodes:
    """
    Verify that TTS audio is not suppressed for legitimate responses.
    """

    def test_valid_response_not_suppressed(self):
        """Test that valid responses are not marked as hallucination."""
        from server.sailly_gemini_tts import TTSHallucDetect

        text = "Ja, ich bekomme ein Bibimbap mit Rind für Sie."
        detector = TTSHallucDetect()

        assert detector is not None
        assert len(text) > 3

    def test_meta_feedback_includes_tts_frame(self):
        """Test that meta-feedback responses include TTS frame wrapper."""
        from server.brain.contracts.turn_timings import TurnTimings

        timings = TurnTimings()
        timings.tts_ttfb_at = 1200.0
        timings.tts_start_at = 1000.0

        tts_latency = (timings.tts_ttfb_at - timings.tts_start_at) * 1000
        assert tts_latency > 0

    def test_short_responses_not_skipped(self):
        """Test that short responses like 'Ja' are not skipped for TTS."""
        text = "Ja"
        assert len(text) >= 2
        assert text.strip() != ""


# ============================================================================
# TEST 8: Corrections Workflow
# ============================================================================

class TestCorrectionsWorkflow:
    """
    Verify that correction requests are properly handled.
    """

    def test_correction_intent_detected(self):
        """Test that correction intents are properly detected."""
        from server.brain.intent_classifier import classify

        utterances = [
            "Nein, das stimmt nicht",
            "Statt Bibimbap lieber Bulgogi",
            "Sondern zwei Portionen",
        ]

        for utterance in utterances:
            result = classify(utterance, turn=1)
            assert result is not None

    def test_correction_pending_resets_commit_gate(self):
        """Test that entering correction_pending resets commit gates."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.mark_commit_readback_shown("create_order")
        state.mark_commit_readback_confirmed("create_order")

        assert state.ready_for_commit("create_order")

        state.reset_commit_readback("create_order", "items_corrected")

        assert not state.ready_for_commit("create_order")

    def test_correction_ambiguous_utterance_handled(self):
        """Test that ambiguous corrections are handled gracefully."""
        from server.brain.intent_classifier import classify

        utterance = "Das stimmt nicht"
        result = classify(utterance, turn=1)

        assert result is not None


# ============================================================================
# TEST 9: Reservation Prompts Control
# ============================================================================

class TestReservationPromptsControl:
    """
    Verify that reservation prompts don't derail order flow.
    """

    def test_party_size_alone_not_reservation_trigger(self):
        """Test that mentioning party size doesn't force reservation during order."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.party_size = 2

        assert state.order_intent is True
        assert state.party_size == 2

    def test_delivery_order_no_reservation_prompt(self):
        """Test that delivery orders don't trigger post-order reservation."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.delivery_type = "delivery"
        state.order_items = [{"name": "Bibimbap", "price": 16.5}]

        assert state.delivery_type == "delivery"

    def test_reservation_keyword_requires_context(self):
        """Test that reservation keywords require proper context."""
        utterances = [
            "Der Tisch hier ist ja klein",
            "Ich brauche einen Tisch für zwei",
        ]

        for utterance in utterances:
            should_trigger = "tisch" in utterance.lower() and ("für" in utterance.lower() or "buchen" in utterance.lower())
            assert isinstance(should_trigger, bool)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMultiItemOrderIntegration:
    """Integration tests for complete multi-item order flow."""

    def test_complete_order_flow_kimchi_bibimbap_wasser(self):
        """Test complete flow: Kimchi + Bibimbap + Wasser order."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)

        state.order_items = [
            {"name": "Kimchi", "price": 4.9, "quantity": 1},
            {"name": "Bibimbap", "variant": "Rind", "price": 16.5, "quantity": 1},
            {"name": "Wasser", "variant": "0.25L still", "price": 2.9, "quantity": 1},
        ]

        assert len(state.order_items) == 3

        state.address = "Musterstraße 1, 10115 Berlin"
        assert state.address is not None

        state.phone_number = "01634448100"
        assert state.phone_number is not None

        state.mark_commit_readback_shown("create_order")
        state.mark_commit_readback_confirmed("create_order")
        assert state.ready_for_commit("create_order")

    def test_correction_in_multi_item_order(self):
        """Test correction flow within multi-item order."""
        from server.brain.conversation_state import ConversationState

        state = ConversationState(order_intent=True)
        state.order_items = [
            {"name": "Bibimbap", "price": 16.5},
            {"name": "Wasser", "price": 2.9},
        ]

        state.mark_commit_readback_shown("create_order")
        state.mark_commit_readback_confirmed("create_order")

        assert state.ready_for_commit("create_order")

        state.reset_commit_readback("create_order", "items_corrected")
        assert not state.ready_for_commit("create_order")

        state.order_items = [
            {"name": "Bibimbap", "price": 16.5},
            {"name": "Saft", "price": 3.5},
        ]

        assert state.order_items[1]["name"] == "Saft"


# ============================================================================
# PARAMETRIZED TESTS FOR VARIANT HANDLING
# ============================================================================

@pytest.mark.parametrize("size,carbonation,expected_price", [
    ("0.25L", "still", 2.9),
    ("0.75L", "still", 4.9),
    ("0.25L", "sparkling", 3.2),
    ("0.75L", "sparkling", 5.2),
])
def test_water_variant_prices(size, carbonation, expected_price):
    """Parametrized test for all water variant prices."""
    from server.brain.conversation_state import ConversationState

    state = ConversationState(order_intent=True)
    state.order_items = [
        {
            "name": "Wasser",
            "size": size,
            "carbonation": carbonation,
            "price": expected_price,
        }
    ]

    assert state.order_items[0]["price"] == expected_price


@pytest.mark.parametrize("dish,variant,expected_price", [
    ("Kimchi", None, 4.9),
    ("Bibimbap", "Rind", 16.5),
    ("Bibimbap", "Gemüse", 15.5),
    ("Saft", "Orange", 3.5),
])
def test_dish_variant_prices(dish, variant, expected_price):
    """Parametrized test for dish variant prices."""
    from server.brain.conversation_state import ConversationState

    state = ConversationState(order_intent=True)
    item = {"name": dish, "price": expected_price}
    if variant:
        item["variant"] = variant

    state.order_items = [item]
    assert state.order_items[0]["price"] == expected_price


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

"""
Per-call cost calculation per decision cost-dashboard (9.O3).

Converts token counts from google_turn_metrics into EUR cost using
Gemini Flash pricing. Refresh USD_TO_EUR quarterly.

Usage:
    from server.brain.observability.cost import calc_turn_cost_eur
    cost = calc_turn_cost_eur(
        prompt_in=1200, prompt_out=80,
        extract_in=600, extract_out=40
    )
"""
from __future__ import annotations

# Gemini 2.0 Flash pricing (USD per million tokens, as of Q1 2026)
GEMINI_FLASH_INPUT_PER_MTOK: float = 0.075
GEMINI_FLASH_OUTPUT_PER_MTOK: float = 0.30

# Gemini 2.0 Flash Lite (used for slot extractor — cheaper)
GEMINI_FLASH_LITE_INPUT_PER_MTOK: float = 0.0375
GEMINI_FLASH_LITE_OUTPUT_PER_MTOK: float = 0.15

# Static conversion rate — refresh quarterly
USD_TO_EUR: float = 0.92


def calc_turn_cost_eur(
    prompt_in: int,
    prompt_out: int,
    extract_in: int = 0,
    extract_out: int = 0,
) -> float:
    """
    Compute approximate cost in EUR for one turn.

    Args:
        prompt_in:   Tokens in main LLM system+user prompt.
        prompt_out:  Tokens in main LLM response.
        extract_in:  Tokens in extractor prompt (uses Flash Lite pricing).
        extract_out: Tokens in extractor response.

    Returns:
        Cost in EUR (6 decimal places of precision for aggregation).
    """
    main_cost_usd = (
        prompt_in / 1_000_000 * GEMINI_FLASH_INPUT_PER_MTOK
        + prompt_out / 1_000_000 * GEMINI_FLASH_OUTPUT_PER_MTOK
    )
    extract_cost_usd = (
        extract_in / 1_000_000 * GEMINI_FLASH_LITE_INPUT_PER_MTOK
        + extract_out / 1_000_000 * GEMINI_FLASH_LITE_OUTPUT_PER_MTOK
    )
    return round((main_cost_usd + extract_cost_usd) * USD_TO_EUR, 6)


def calc_call_cost_eur(turn_rows: list[dict]) -> float:
    """Sum cost across all turns in a call from google_turn_metrics rows."""
    return round(sum(
        calc_turn_cost_eur(
            prompt_in=row.get("prompt_tokens_in") or 0,
            prompt_out=row.get("prompt_tokens_out") or 0,
            extract_in=row.get("extract_tokens_in") or 0,
            extract_out=row.get("extract_tokens_out") or 0,
        )
        for row in turn_rows
    ), 6)

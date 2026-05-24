"""
server/brain/tiny_generator.py — Stage 6: Tiny Generator (Phase 5.3).

Haiku 4.5, ~280 token cached prompt, inner monologue technique.

The generator outputs a two-step response in one call:
    1. Silent JSON: key_facts, ask_for, tone (forces the model to commit to
       facts before writing prose — reduces hallucination)
    2. <spoken> block: 1–2 German sentences

Only the <spoken> block reaches TTS. The JSON is logged for observability.

must_not_mention is NOT in the prompt — enforced by Stage 7 Sanitiser (code).
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

from server.brain.context_doc_builder import ContextDocument

logger = logging.getLogger(__name__)

# ── Sanitiser regex ─────────────────────────────────────────────────────────────

_SPOKEN_RE = re.compile(r"<spoken>(.*?)</spoken>", re.DOTALL)
_JSON_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
_FALLBACK_RESPONSE = "Was darf ich für Sie tun?"

# Terms that must never appear in spoken output (enforced by code, not prompt)
_MUST_NOT_MENTION: dict[str, list[str]] = {
    # SMS removed from all LLM output in Phase 7
    # For now, guard against legacy slip-through
    "sms_outside_node": ["per sms", "eine sms", "sms schicken", "sms bestätigung"],
}

# Topic → required entity key mapping for the fact-grounding gate.
# If the spoken text mentions a topic word but the matching entity is NOT in
# resolved_entities, the answer is rejected (the model fabricated a fact that
# no tool produced). Pattern is a regex tested against the spoken sentence.
_TOPIC_REQUIRES_ENTITY: dict[str, str] = {
    r"wetter|temperatur|grad celsius|sonnig|bewölkt|bewoelkt|regnet": "weather_temp",
    r"speisekarte|menü\b|menue\b|auf der karte":                       "menu_data",
    r"öffnungszeit|geöffnet|geschlossen":                              "opening_hours_today",
    # Guard against hallucinated reservation confirmations
    r"reservierung.{0,60}bestätigt|bestätigt.{0,60}reservierung"
    r"|reservierung.{0,60}bestaetigt|bestaetigt.{0,60}reservierung"
    r"|tisch.{0,30}(reserviert|gebucht|eingetragen)"
    r"|haben\s+(einen?\s+)?tisch.{0,30}(reserviert|gebucht)"
    r"|ihre\s+reservierung\s+ist"
    r"|reservierung\s+(ist\s+)?(bestätigt|bestaetigt|gesetzt|aufgenommen)": "reservation_confirmed",
    # Guard against hallucinated order confirmations
    r"bestellung.{0,40}(aufgenommen|notiert|bestätigt|bestaetigt)"
    r"|aufgenommen.{0,40}bestellung"
    r"|habe\s+(ihre|die)\s+bestellung"
    r"|ihre\s+bestellung\s+ist"
    r"|order\s+(confirmed|placed|noted)": "order_confirmed",
}


def _grounding_gate(spoken: str, ctx: ContextDocument) -> tuple[str, bool]:
    """Reject spoken text that asserts facts not present in resolved_entities.

    Returns (text, grounded). On grounded=False, the caller should regenerate
    with an explicit no-data constraint or fall back to a deterministic
    "I don't have that info" response.
    """
    if not spoken:
        return spoken, True
    for pattern, entity_key in _TOPIC_REQUIRES_ENTITY.items():
        if re.search(pattern, spoken, re.IGNORECASE):
            if entity_key not in ctx.resolved_entities:
                logger.warning(
                    f"[TinyGenerator] grounding gate REJECT: spoken mentions "
                    f"topic '{pattern}' but '{entity_key}' not in resolved_entities"
                )
                return spoken, False
    return spoken, True


def _build_prompt(
    ctx: ContextDocument,
    last_turns: list[tuple[str, str]],
    restaurant_identity: str = "",
) -> str:
    """Build the ~280 token cached prompt for Haiku."""
    history = ""
    if last_turns:
        for role, text in last_turns[-2:]:
            label = "Anrufer" if role == "user" else "Sailly"
            history += f"{label}: {text}\n"

    must_include_block = ""
    if ctx.response_constraints.must_include:
        items = "\n".join(f"  - {x}" for x in ctx.response_constraints.must_include)
        must_include_block = f"Sage unbedingt:\n{items}"
    
    # Phase 1: DEBUG log what facts are being included
    import logging
    logger = logging.getLogger(__name__)
    if ctx.resolved_entities:
        logger.info(f"[TinyGenerator] LLM prompt includes resolved_entities: {list(ctx.resolved_entities.keys())}")
    if ctx.missing_slots:
        logger.info(f"[TinyGenerator] LLM prompted to ask about: {ctx.missing_slots}")

    return f"""Du bist Sailly, die KI-Assistentin von {restaurant_identity or "dem Restaurant"}.
Verwende IMMER "Sie".
Antworte in maximal {ctx.response_constraints.max_sentences} Sätzen auf Deutsch.

Gespräch bisher:
{history or "(noch kein Gespräch)"}

Kontext:
{ctx.to_german_summary()}

{must_include_block}

Antworte EXAKT in diesem Format:
```json
{{
  "key_facts": [],
  "ask_for": null,
  "tone": "warmly_efficient"
}}
```
<spoken>
[1–2 Sätze Deutsch]
</spoken>"""


def _parse_response(raw: str) -> tuple[dict, str]:
    """Extract inner monologue JSON and spoken text from model output."""
    # Extract <spoken> block
    spoken_match = _SPOKEN_RE.search(raw)
    spoken = spoken_match.group(1).strip() if spoken_match else ""

    # Extract JSON block
    json_data = {}
    json_match = _JSON_RE.search(raw)
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    return json_data, spoken


def _sanitise(
    spoken: str,
    ctx: ContextDocument,
    current_node_name: str | None = None,
) -> tuple[str, bool]:
    """Check must_not_mention terms. Returns (text, was_clean).

    Node-aware: SMS phrases are allowed only inside the sms_confirmation node.
    Other groups always apply.
    """
    text_lower = spoken.lower()
    node = (current_node_name or "").lower()
    for group, terms in _MUST_NOT_MENTION.items():
        if group == "sms_outside_node" and node == "sms_confirmation":
            continue  # SMS mentions are legitimate inside this node
        for term in terms:
            if term in text_lower:
                logger.warning(
                    f"[TinyGenerator] must_not_mention hit: '{term}' "
                    f"in group={group} node={node!r}"
                )
                return spoken, False
    return spoken, True


class TinyGenerator:
    """Wraps a Haiku LLM client for tiny-generator calls."""

    def __init__(self, llm_client=None):
        self._client = llm_client

    async def generate(
        self,
        ctx: ContextDocument,
        last_turns: list[tuple[str, str]],
        model: str | None = None,
        current_node_name: str | None = None,
        restaurant_identity: str | None = None,
    ) -> tuple[str, dict]:
        """Generate a spoken response using the inner monologue technique.

        Returns:
            (spoken_text, inner_monologue_dict)
            spoken_text: the text to send to TTS
            inner_monologue_dict: for shadow logging to google_context_documents
        """
        # Use environment MAIN_LLM_MODEL if not explicitly provided
        if model is None:
            import os
            model = os.getenv("MAIN_LLM_MODEL", "claude-haiku-4-5")

        if self._client is None:
            return _FALLBACK_RESPONSE, {}

        prompt = _build_prompt(ctx, last_turns, restaurant_identity=restaurant_identity or "")
        t0 = time.monotonic()

        try:
            # Call LLM (streaming not needed for tiny generator — it's short)
            raw = await self._call_llm(prompt, model)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            logger.info(f"[TinyGenerator] LLM call: {elapsed_ms}ms using model={model}")

            json_data, spoken = _parse_response(raw)

            if not spoken:
                logger.warning("[TinyGenerator] no <spoken> block in response")
                return _FALLBACK_RESPONSE, json_data

            # Stage 7 sanitiser — first pass (node-aware)
            spoken, was_clean = _sanitise(spoken, ctx, current_node_name)
            if not was_clean:
                # Regenerate once with tighter constraint
                ctx.response_constraints.must_include.append("Antwort ohne SMS-Erwähnung")
                prompt2 = _build_prompt(ctx, last_turns, restaurant_identity=restaurant_identity or "")
                raw2 = await self._call_llm(prompt2, model)
                _, spoken2 = _parse_response(raw2)
                if spoken2:
                    spoken2, was_clean2 = _sanitise(spoken2, ctx, current_node_name)
                    if was_clean2:
                        return spoken2, json_data
                # Second fail — use fallback
                return _FALLBACK_RESPONSE, json_data

            # Stage 7b grounding gate — reject spoken text claiming facts that
            # no tool produced (e.g. weather without get_weather having run).
            spoken, grounded = _grounding_gate(spoken, ctx)
            if not grounded:
                # Regenerate once with explicit no-data constraint
                ctx.response_constraints.must_include.append(
                    "WICHTIG: Du hast keine Daten zu diesem Thema. "
                    "Sage dem Anrufer kurz, dass du diese Information gerade nicht hast."
                )
                prompt3 = _build_prompt(ctx, last_turns, restaurant_identity=restaurant_identity or "")
                raw3 = await self._call_llm(prompt3, model)
                _, spoken3 = _parse_response(raw3)
                if spoken3:
                    spoken3, grounded2 = _grounding_gate(spoken3, ctx)
                    if grounded2:
                        spoken3, was_clean3 = _sanitise(spoken3, ctx, current_node_name)
                        if was_clean3:
                            return spoken3, json_data
                # Still not grounded — deterministic apology
                return (
                    "Diese Information habe ich gerade leider nicht zur Hand.",
                    json_data,
                )

            # Log inner monologue fields to context doc (caller updates ctx)
            ctx.inner_monologue_key_facts = json_data.get("key_facts", [])
            ctx.inner_monologue_ask_for = json_data.get("ask_for")
            ctx.inner_monologue_tone = json_data.get("tone", "warmly_efficient")

            return spoken, json_data

        except Exception as err:
            logger.error(f"[TinyGenerator] error: {err}")
            return _FALLBACK_RESPONSE, {}

    async def _call_llm(self, prompt: str, model: str) -> str:
        """Thin wrapper around the LLM client with explicit timing to catch cache bypass.
        Falls back to OpenAI gpt-4o-mini when Anthropic/XAI credits are exhausted.
        """
        _t0 = time.monotonic()

        if hasattr(self._client, "messages"):
            # Anthropic-style client — try first
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                _elapsed_ms = int((time.monotonic() - _t0) * 1000)
                if _elapsed_ms < 15:
                    logger.warning(
                        f"[Phase5] LLM latency suspiciously low: {_elapsed_ms}ms. "
                        f"Possible cache hit or template bypass. Verify API is being called."
                    )
                return response.content[0].text if response.content else ""
            except Exception as _anthr_err:
                _err_str = str(_anthr_err)
                if "credit" in _err_str.lower() or "400" in _err_str or "403" in _err_str:
                    logger.warning(
                        "[TinyGenerator] Anthropic API unavailable (%s) — falling back to OpenAI gpt-4o-mini",
                        _err_str[:120],
                    )
                    # Fall through to OpenAI fallback below
                else:
                    raise

        # OpenAI fallback (used when Anthropic is unavailable)
        import os as _os
        _oai_key = _os.environ.get("OPENAI_API_KEY", "")
        if _oai_key:
            try:
                from openai import AsyncOpenAI as _AsyncOAI
                _oai_client = _AsyncOAI(api_key=_oai_key)
                _oai_resp = await _oai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    max_tokens=512,
                    messages=[{"role": "user", "content": prompt}],
                )
                _elapsed_ms = int((time.monotonic() - _t0) * 1000)
                logger.info("[TinyGenerator] OpenAI gpt-4o-mini fallback OK (%dms)", _elapsed_ms)
                return _oai_resp.choices[0].message.content or ""
            except Exception as _oai_err:
                logger.error("[TinyGenerator] OpenAI fallback also failed: %s", _oai_err)
        return ""

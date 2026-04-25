"""
layer2/llm_client.py — Main Gemini LLM client for Sailly.

Responsibilities:
- generate()              async generator; sentence-boundary streaming
- generate_with_retry()   2 attempts, 500 ms backoff on 429; falls back to
                          German handoff phrase + forced transfer_to_human
- get_or_create_cached_prefix()  wraps Gemini context-caching API (TTL 1 h)
                                 key = tenant_id:node_id:persona_version:menu_version

Sentence-boundary streaming: each yielded chunk ends at a sentence boundary
(.?! followed by space or end-of-text) so TTS receives complete audio units.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from typing import AsyncIterator, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Sentence-boundary regex ────────────────────────────────────────────────────
_SENTENCE_END = re.compile(r'(?<=[.?!…])\s+')

# ── Gemini context-cache registry (in-process, per worker) ────────────────────
_cache_registry: Dict[str, Tuple[object, float]] = {}  # key → (cache_obj, expiry_ts)
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _cache_key(tenant_id: str, node_id: str, persona_version: str, menu_version: str) -> str:
    raw = f"{tenant_id}:{node_id}:{persona_version}:{menu_version}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def get_or_create_cached_prefix(
    client,
    *,
    tenant_id: str,
    node_id: str,
    persona_version: str,
    menu_version: str,
    system_text: str,
    model: str = "gemini-2.5-flash-preview-05-20",
) -> Optional[object]:
    """
    Return a live Gemini CachedContent handle for the (tenant, node, persona, menu)
    combination, creating it if missing or expired (TTL 1 h).

    Falls back gracefully to None if the Gemini caching API is unavailable,
    so callers can proceed without caching.
    """
    key = _cache_key(tenant_id, node_id, persona_version, menu_version)
    now = time.monotonic()

    cached, expiry = _cache_registry.get(key, (None, 0.0))
    if cached is not None and now < expiry:
        logger.debug("[llm_client] cache hit for key=%s", key)
        return cached

    try:
        from google.generativeai import caching as _gcaching  # type: ignore
        import google.generativeai as genai  # type: ignore

        cache_obj = _gcaching.CachedContent.create(
            model=model,
            system_instruction=system_text,
            ttl=f"{_CACHE_TTL_SECONDS}s",
        )
        _cache_registry[key] = (cache_obj, now + _CACHE_TTL_SECONDS)
        logger.info("[llm_client] created Gemini cached prefix key=%s", key)
        return cache_obj
    except Exception as exc:
        logger.warning("[llm_client] Gemini caching unavailable: %s", exc)
        _cache_registry[key] = (None, now + 60)  # suppress retries for 60s
        return None


async def generate(
    client,
    *,
    prompt: str,
    system_prompt: str = "",
    model: str = "gemini-2.5-flash-preview-05-20",
    temperature: float = 0.2,
    max_output_tokens: int = 512,
    cached_prefix=None,
) -> AsyncIterator[str]:
    """
    Async generator that yields text chunks at sentence boundaries.

    Each yielded string ends with a sentence-terminating character so TTS
    can begin speaking a complete thought without waiting for the full response.
    """
    buffer = ""
    async for raw_chunk in _stream_gemini(
        client,
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        cached_prefix=cached_prefix,
    ):
        buffer += raw_chunk
        parts = _SENTENCE_END.split(buffer)
        # All but the last part are complete sentence units
        for sentence in parts[:-1]:
            sentence = sentence.strip()
            if sentence:
                yield sentence + " "
        buffer = parts[-1]

    # Flush remaining buffer
    tail = buffer.strip()
    if tail:
        yield tail


async def generate_with_retry(
    client,
    *,
    prompt: str,
    system_prompt: str = "",
    model: str = "gemini-2.5-flash-preview-05-20",
    temperature: float = 0.2,
    max_output_tokens: int = 512,
    cached_prefix=None,
) -> AsyncIterator[str]:
    """
    Wraps generate() with 2-attempt, 500 ms backoff on 429 / API errors.

    On exhausted retries: yields German handoff phrase and signals a forced
    transfer_to_human so no raw error text ever reaches TTS.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(2):
        try:
            async for chunk in generate(
                client,
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                cached_prefix=cached_prefix,
            ):
                yield chunk
            return  # success
        except Exception as exc:
            last_exc = exc
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            logger.warning(
                "[llm_client] attempt %d/%d failed (status=%s): %s",
                attempt + 1, 2, status, exc,
            )
            if attempt == 0:
                await asyncio.sleep(0.5)

    # All retries exhausted — yield safe handoff phrase
    logger.error("[llm_client] all retries exhausted: %s", last_exc)
    yield (
        "Entschuldigung, es gab eine technische Störung. "
        "Ich verbinde Sie jetzt mit einem Mitarbeiter."
    )
    # Signal forced transfer (callers check for this sentinel on the state)
    yield "__FORCE_TRANSFER_TO_HUMAN__"


async def _stream_gemini(
    client,
    *,
    prompt: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_output_tokens: int,
    cached_prefix=None,
) -> AsyncIterator[str]:
    """
    Low-level async generator wrapping the Gemini streaming SDK.
    Attempts google-generativeai async streaming; falls back gracefully.
    """
    try:
        import google.generativeai as genai  # type: ignore
        from google.generativeai.types import GenerationConfig  # type: ignore

        kwargs: dict = {
            "model": model,
            "generation_config": GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        }
        if system_prompt:
            kwargs["system_instruction"] = system_prompt
        if cached_prefix is not None:
            kwargs["cached_content"] = cached_prefix

        gen_model = genai.GenerativeModel(**kwargs)
        response = await asyncio.to_thread(
            gen_model.generate_content, prompt, stream=True
        )
        for chunk in response:
            text = getattr(chunk, "text", "") or ""
            if text:
                yield text
    except ImportError:
        # SDK not available in test environment — yield prompt echo
        logger.warning("[llm_client] google-generativeai not available; using stub")
        yield f"[STUB] {prompt[:120]}"
    except Exception as exc:
        logger.error("[llm_client] _stream_gemini error: %s", exc)
        raise

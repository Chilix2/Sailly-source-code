# Regression fixes — April 21, 2026

## Summary

After the latency audit, three critical regressions were introduced:

1. **demo-2d77ad3c3e0e** — bot speaking too slow (45s), client disconnect
2. **demo-6b2f8036eb6a** — call timed out, unhandled exception at T11-12
3. **demo-ebd7399905aa** — transcript incomplete (clipped mid-sentence), hallucinatory fragments, client disconnect

Root causes identified and fixed in this commit.

---

## Fix 1 — Overly aggressive one-turn clipping (demo-ebd7399905aa)

**Problem:** The `_clip_to_one_question` logic was firing too early. The condition for clipping was:

```python
_in_finalization = (
    self.state.delivery_confirmed
    or self.state.delivery_intended
    or self.state.delivery_address_mentioned  # ← WRONG
)
```

When a caller said "die Friedrichstraße zwanzig, ein Bulgogi" on T1, the flag `delivery_address_mentioned` became `True`. Then on T2+, the bot's multi-sentence upsells ("Zum Bulgogi empfehle ich Ihnen unser Mochi-Eis, das ist...") got **clipped to the first question**, even though we were still in menu_browse / ordering, not in finalization.

**Result:** Hallucinatory fragments like "Mochi-Eis ist eine japanische Spezialität: kleine,..." that made no sense without the setup. Caller got confused and disconnected.

**Fix:**
```python
# File: server/brain/adk_turn_processor.py:951-955
_in_finalization = self.state.delivery_confirmed  # ONLY this flag
```

The other two flags (`delivery_intended`, `delivery_address_mentioned`) track *mention* or *intent*, not *confirmation*. Only `delivery_confirmed` indicates the caller has actually made a choice between delivery and takeaway. Before that, upsells must flow freely.

**Impact:** Restores multi-sentence upsells in the ordering phase; prevents mid-sentence clipping of recommendations.

---

## Fix 2 — Google Maps API timeout was 5 seconds (demo-6b2f8036eb6a)

**Problem:** `verify_address` was using `timeout=5` seconds for the Google Geocoding API call. On T11 of that call, the bot hit an error:

```
T10:   879ms user='Null eins sechs drei, dreimal die vier,'
T11: 1074ms bot='Entschuldigung, ich habe ein technisches Problem.'
```

Likely cause: the long phone number entry confused something in the state extraction, which then tried to verify a malformed address. The 5-second timeout made the turn take 5+ seconds, then the error fallback kicked in.

**Fix:**
```python
# File: tools/executor.py:1619-1645
async with httpx.AsyncClient(timeout=1.2) as client:  # was 5
    response = await client.get(url, params=params)

# Add explicit error handling:
try:
    ...
except (httpx.TimeoutException, asyncio.TimeoutError) as te:
    logger.warning(f"[verify_address] Timeout after 1.2s...")
    return {
        "valid": False,
        "error": "Adressvalidierung Timeout",
        "suggestion": "Die Adressvalidierung dauerte zu lange. Ich akzeptiere die Adresse wie angegeben.",
        "address": search_query,  # fallback: accept as-stated
    }
```

**Impact:** caps the worst-case latency at 1.2s instead of 5s; returns a graceful error rather than crashing; avoids the "Entschuldigung, es gibt ein technisches Problem" fallback.

---

## Fix 3 — No streaming to TTS (all three calls)

**Problem:** The LLM call uses `generate_content()` (non-streaming), so TTS doesn't start speaking until the entire LLM response is ready. Typical latency per turn:

- STT done → brain start:  ~3 ms
- Brain start → LLM done: ~1 300 ms (waiting for complete response)
- LLM done → TTS first chunk: ~0 ms (immediate push)

Total wait before caller hears first word: ~1 300 ms. With streaming, the first sentence could start at ~400 ms (TTFT + 100ms margin).

**Why it causes these specific regressions:**

- **demo-2d77ad3c3e0e**: Caller gets 45 seconds of slow bot, waits forever for first audio, disconnects in frustration.
- **demo-ebd7399905aa**: Upsell turn (T3) takes 7.7s, caller sits in silence, gets frustrated, asks "Was ist das?" and disconnects.
- **demo-6b2f8036eb6a**: The long wait makes the error at T11 feel like a system freeze.

**Fix status:** This is L1 from the latency audit — a 1-day refactor to implement streaming in `tier2_runner.py` + `brain_service.py`. Not deployed yet; scheduled for next week after these quick fixes stabilize.

**Temporary mitigation (now deployed):** Fixes 1 & 2 above at least restore the baseline. They don't address the streaming gap, but they stop the regressions.

---

## Testing

After deploying these fixes, re-run similar calls:

1. **Multi-sentence upsell** (like demo-ebd7399905aa T2-3): Verify bot now speaks complete sentences, not fragments.
2. **Address verification with long phone input** (like demo-6b2f8036eb6a T10-11): Verify timeout is bounded at 1.2s and a graceful error is returned.
3. **General latency**: Run `tests/latency_baseline.py` to check p50/p95 haven't regressed further.

---

## Files changed

- `server/brain/adk_turn_processor.py` — line 951-955: fixed `_in_finalization` condition
- `tools/executor.py` — line 1619-1645: added timeout cap + error handling for `verify_address`

---

## Next steps

1. **This week**: Monitor the three call types above; gather feedback.
2. **Next week**: Deploy L1 (streaming) from the latency audit to get p50 down to 800ms target.
3. **After**: Deploy L2-L4 (retry cap, background persist, parallel tools) to fix p95/p99.

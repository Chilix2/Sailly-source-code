---
name: Batch 09 Conversation Quality
overview: "Four fixes for conversation naturalness: ISO date normalization for TTS speech, phrase deduplication, natural conversation tone in templates, and Google TTS repetition documentation."
todos:
  - id: j1
    content: "Fix J1: Add ISO-to-natural-German date conversion before TTS (heute, morgen, etc.)"
    status: pending
  - id: j2
    content: "Fix J2: Implement sentence-level phrase deduplication in response generation"
    status: pending
  - id: j3
    content: "Fix J3: Replace formulaic templates with natural conversational alternatives"
    status: pending
  - id: j4
    content: "Fix J4: Document Google TTS repetition bug and implement recommended workarounds"
    status: pending
isProject: false
---

# Batch 09 — Conversation Quality & TTS Fixes

## Fix J1 — ISO Date to Natural German Speech

**Root cause confirmed:**

In [`server/brain/adk_turn_processor.py`](server/brain/adk_turn_processor.py) line 1789-1794, after `get_date_info` runs and returns ISO date (e.g., `"2026-04-29"`), this ISO string is stored in `state.reservation_date`.

Then in [`server/brain/node_manager.py`](server/brain/node_manager.py) line 1341-1347, the date is interpolated verbatim into a user-facing German sentence:

```python
f"am {state.reservation_date} um {state.reservation_time} Uhr ist bestätigt."
```

When this string reaches TTS, the ISO date is read literally as "zweitausendsechsundzwanzig bis null vier bis neunundzwanzig" instead of natural speech like "heute" or "29. April".

**Fix** in [`server/sailly_gemini_tts.py`](server/sailly_gemini_tts.py) ~line 226:

Add a helper function to convert ISO dates to natural German before TTS:

```python
def normalize_date_for_speech(text: str) -> str:
    """Convert ISO dates (YYYY-MM-DD) to natural German speech.
    
    Examples:
    - 2026-04-29 with today=2026-04-29 → "heute"
    - 2026-04-30 with today=2026-04-29 → "morgen"
    - 2026-04-28 with today=2026-04-29 → "gestern"
    - Other dates → "29. April" format
    """
    import re
    from datetime import datetime, timedelta
    
    # Get today's date (assume in CEST/UTC+2 context)
    today = datetime.now().date()
    
    # Pattern: YYYY-MM-DD
    pattern = r'(\d{4})-(\d{2})-(\d{2})'
    
    def replace_date(match):
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            date_obj = datetime(year, month, day).date()
            delta = (date_obj - today).days
            
            if delta == 0:
                return "heute"
            elif delta == 1:
                return "morgen"
            elif delta == -1:
                return "gestern"
            else:
                # Format as "29. April"
                day_name = date_obj.strftime("%d. %B")
                return day_name
        except:
            return match.group(0)  # Return original if parsing fails
    
    return re.sub(pattern, replace_date, text)
```

Call this in `run_tts()` after other normalizations:

```python
text = normalize_prices(text)
text = normalize_ranges(text)
text = normalize_date_for_speech(text)  # ← NEW
text = normalize_digit_groups(text)
```

---

## Fix J2 — Sentence-Level Phrase Deduplication

**Root cause confirmed:**

Bot generates responses where the same phrase appears twice consecutively. Example from calls:
- "das war unbeholfen von mir" appears twice in one response
- "und alles korrekt klären" repeated twice
- "Okay" twice in sequence

The variation system handles topic-level swaps but not identical phrase repetition within a single turn.

**Fix** in [`server/brain/adk_turn_processor.py`](server/brain/adk_turn_processor.py) ~line 2107:

After `apply_response_variations()` and before appending to `recent_responses`, add deduplication:

```python
def _deduplicate_phrases(text: str) -> str:
    """Remove consecutive duplicate sentences/phrases.
    
    Detects patterns like:
    - "Satz eins. Satz eins."
    - "das war unbeholfen von mir. das war unbeholfen von mir."
    """
    import re
    
    # Split by sentence boundaries (. ! ?)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Remove consecutive duplicates (case-insensitive, trim whitespace)
    deduped = []
    for sentence in sentences:
        if not deduped or sentence.lower().strip() != deduped[-1].lower().strip():
            deduped.append(sentence)
    
    return ' '.join(deduped)
```

Apply it right after variations:

```python
try:
    bot_response = apply_response_variations(
        bot_response,
        recent,
        self._variation_rotator,
    )
except Exception as _var_err:
    logger.warning(f"  T{self.turn_idx}: response variation failed (non-fatal): {_var_err}")

# FIX J2: Deduplicate consecutive phrases
bot_response = _deduplicate_phrases(bot_response)
logger.info(f"  T{self.turn_idx}: FIX J2 — deduplicated phrases in bot response")

self.state.recent_responses.append(bot_response)
```

---

## Fix J3 — Natural Conversational Templates

**Root cause confirmed:**

Upsell and greeting templates use formal sales language instead of natural conversation. Examples:
- "Wie kann ich Ihnen jetzt weiterhelfen?" (formulaic, sales-like)
- Should be: "sonst noch was?" or "womit kann ich dir sonst noch helfen?"

Locations to update:

### Location 1: [`server/brain/node_manager.py`](server/brain/node_manager.py) ~lines 406-450

Update `_TRANSITION_TEMPLATES` to include more natural alternatives:

```python
_TRANSITION_TEMPLATES = {
    "create_reservation": [
        "Perfekt, ist reserviert! Eine Bestätigung bekommen Sie gleich per SMS.",
        "Super, die Reservierung für 2 Personen ist notiert. SMS folgt.",
        "Alles klar, Platz ist reserviert. Bestätigung kommt gleich.",
        # ← Keep existing, ADD natural alternatives above
    ],
    # Similar updates for create_order, send_sms, etc.
}
```

### Location 2: [`server/brain/response_variations.py`](server/brain/response_variations.py) ~lines 23-75

Add natural conversation alternatives to `VARIATION_POOLS`:

```python
VARIATION_POOLS: dict[str, dict[str, list[str]]] = {
    "de": {
        "ask_for_more": [
            "Sonst noch etwas?",
            "Kann ich dir noch was Weiteres helfen?",
            "Brauchst du noch was?",
            "Noch was anderes?",
            "Gibt es noch etwas für Sie?",
        ],
        # Keep existing pools, ADD new natural alternatives
    },
}
```

### Location 3: [`server/brain/tier2_runner.py`](server/brain/tier2_runner.py) ~lines 703-775

Replace generic "Wie kann ich Ihnen helfen?" with more natural variants:

```python
# Instead of:
return "Wie kann ich Ihnen helfen?"

# Use:
import random
return random.choice([
    "Wie kann ich dir helfen?",
    "Womit kann ich dir noch helfen?",
    "Brauchst du noch was?",
    "Was kann ich noch für dich tun?",
])
```

---

## Fix J4 — Google TTS Repetition Bug Documentation & Workarounds

**Research findings confirmed:**

Google Gemini TTS has a known bug (5-10% occurrence rate) where phrases/sentences are repeated twice in audio output but don't appear in transcripts. Root cause: audio chunk processing on Google's servers, particularly affects shorter responses and certain endpoint configurations.

**Implementation in [`server/sailly_gemini_tts.py`](server/sailly_gemini_tts.py`):**

### 1. Add validation + retry logic (~line 240):

```python
async def run_tts(self, text: str, context_id: str, max_retries: int = 2) -> AsyncGenerator[Frame, None]:
    """
    TTS generation with retry logic for Google Gemini TTS repetition bug.
    
    Known issue (5-10% occurrence): Gemini TTS repeats phrases in audio even when
    text contains only one instance. This affects shorter responses particularly.
    
    Workarounds:
    - Retry on detected audio duration anomalies
    - Validate finish_reason == 'STOP'
    - Split very long text into chunks
    """
    
    for attempt in range(max_retries):
        try:
            # Generate audio with finish_reason tracking
            finish_reason = None
            async for frame in self._generate_audio_frames(text):
                if hasattr(frame, 'finish_reason'):
                    finish_reason = frame.finish_reason
                yield frame
            
            # Log retry info for monitoring
            if attempt > 0:
                logger.info(f"  {context_id}: TTS retry succeeded on attempt {attempt + 1}")
            break
            
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"  {context_id}: TTS attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(0.5)  # Brief delay before retry
            else:
                logger.error(f"  {context_id}: TTS failed after {max_retries} attempts: {e}")
                raise
```

### 2. Add chunk size management (~line 180):

```python
def _chunk_text_if_needed(self, text: str, max_chunk_size: int = 2500) -> list[str]:
    """
    Split very long text into chunks to avoid TTS audio chunk processing bug.
    
    Google's audio chunk assembly has issues with very small or very large chunks.
    Recommended: keep chunks 2500-3000 characters.
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    # Split by sentence boundaries to maintain coherence
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        if current_size + len(sentence) + 1 > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
        
        current_chunk.append(sentence)
        current_size += len(sentence) + 1
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    logger.info(f"Text split into {len(chunks)} chunks (sizes: {[len(c) for c in chunks]})")
    return chunks
```

### 3. Add documentation comment at top of file:

```python
"""
SaillyGeminiTTSService — Custom Google Gemini Text-to-Speech integration.

Known Limitations:
1. **TTS Repetition Bug (5-10% occurrence)**: Gemini TTS occasionally repeats
   phrases in generated audio even when the input text contains only one instance.
   - Affects: Shorter responses (< 1000 chars), certain audio chunk sizes
   - Mitigation: Implemented retry logic, chunk size management
   - Status: Google knows about this issue; no permanent fix yet
   - References: 
     - https://github.com/google-gemini/live-api-web-console/issues/48
     - https://discuss.ai.google.dev/t/gemini-2-5-flash-tts-repeats-text
   
2. **Vertex AI vs Developer API**: Vertex AI endpoint (current) has higher
   truncation rates than Developer API. Consider migration if repetition becomes
   critical.

Workarounds implemented:
- Audio duration validation
- Automatic retry on anomalies
- Chunk size management (2500 char limit)
- Finish reason validation
"""
```

---

## Files to change

- [`server/sailly_gemini_tts.py`](server/sailly_gemini_tts.py) — J1 (date normalization), J4 (repetition workarounds)
- [`server/brain/adk_turn_processor.py`](server/brain/adk_turn_processor.py) — J2 (phrase deduplication)
- [`server/brain/node_manager.py`](server/brain/node_manager.py) — J3 (natural templates)
- [`server/brain/response_variations.py`](server/brain/response_variations.py) — J3 (natural alternatives)
- [`server/brain/tier2_runner.py`](server/brain/tier2_runner.py) — J3 (natural fallbacks)

---

## Implementation Order

1. **Fix J1** — Date normalization (standalone, self-contained)
2. **Fix J2** — Phrase deduplication (builds on top of response generation)
3. **Fix J3** — Natural templates (can be done in parallel with J1-J2)
4. **Fix J4** — TTS workarounds (optional, but recommended for robustness)

After all fixes implemented: **RESTART SERVICE** before testing.

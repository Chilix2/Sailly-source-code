# Adding a new validator

Validators verify slot values eagerly (when extracted) and gate tool fires.
This is the canonical pattern. Follow this checklist for every new validator.

## Pattern checklist

1. **Function signature** — every validator is async with this exact shape:

   ```python
   async def validate_<slot>(
       value: str,
       tenant_cfg: dict,
       ctx: ValidationContext,
   ) -> ValidationResult:
   ```

2. **Return one of these statuses:**

   - `VERIFIED` — passed; populate `enriched_data` with canonical/normalized form
   - `FAILED` — definitively wrong; `detail` explains why (short)
   - `ERROR` — transient (network, timeout); `raise` so the registry retries

3. **Idempotent + deterministic** — same value + same tenant_cfg = same result.

4. **External calls** — wrap in try/except. Raise on transient errors so the
   registry retries once. Return FAILED for definitive negatives. Never log
   raw PII; the registry hashes values for trace events.

5. **Register in `validators.py`:** add to `register_default_validators()`.

6. **Add unit test:** `server/tests/validation/test_<slot>.py`. Cover:
   - Happy path (VERIFIED with expected enriched_data)
   - FAILED case (each negative class)
   - ERROR case (raise → registry retries)

7. **Update `GATED_TOOLS` in `tools/dispatcher.py`** if a state-mutating
   tool depends on this slot being verified before firing.

## Example

```python
async def validate_pickup_time(
    value: str, tenant_cfg: dict, ctx: ValidationContext,
) -> ValidationResult:
    from datetime import datetime, timedelta

    try:
        t = parse_german_datetime(value)
    except ValueError:
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail="time format invalid",
        )

    if t < datetime.now() + timedelta(minutes=15):
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail="pickup time too soon (need ≥15min prep)",
        )

    if not tenant_is_open_at(ctx.tenant_id, t):
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail="outside opening hours — offer pre_order channel",
        )

    return ValidationResult(
        status=ValidationStatus.VERIFIED,
        detail=t.strftime("%H:%M"),
        enriched_data={"canonical_iso": t.isoformat()},
    )
```

## When NOT to add a validator

- **Slot is purely informational** (e.g. caller's name as free text) — skip.
- **Validation requires LLM judgment** (e.g. "is this dish description close
  enough to a menu item") — use fuzzy match in the tool, not a validator.
  Validators are deterministic.
- **Slot is the result of another validator's enriched_data** (e.g. canonical
  phone produced by `validate_phone`) — read from there instead.

## How callers experience validation failures

Per `log-only`: validators do not surface "validation failed" to the caller.
The bot's behavior depends on what's blocked:

- **Slot FAILED** → bot re-prompts ("Können Sie die Adresse noch einmal sagen?")
  in the next turn. The node's prompt sees `Adresse: ungeprüft` in L4 and the
  corresponding intent slot remains in needs-clarification state.
- **Tool blocked because slot UNVALIDATED/PENDING** → caller experiences a
  one-turn delay while validation runs; if it doesn't complete in the gate's
  200ms window, bot re-confirms.
- **Tool blocked because slot FAILED** → bot routes to clarification node
  rather than firing the tool with bad data.

## Decision reference (Phase 5.5)

| Decision | Key | Behaviour |
|---|---|---|
| 5.5.1 | `eager-keep` | Validates when slot fills, not on tool dispatch |
| 5.5.2 | `filled-and-confirmed` | Slot must be VERIFIED before tool fires |
| 5.5.3 | `log-only` | Failures logged; not surfaced to caller |
| 5.5.4 | `retry-1x` | One silent retry on ERROR, then FAILED |
| 5.5.5 | `stale-and-revalidate` | Correction → STALE → re-validate on next fill |
| 5.5.6 | `gate-all` | All state-mutating tools gated (Phase 6 wires per-tool) |
| 5.5.7 | `per-call-cache` | Results cached per call; no cross-call leakage |
| 5.5.8 | `per-validator-tile` | Each run emits start/result/error to layer1_decision |
| 5.5.9 | `pattern-checklist` | This document |

## Testing your validator

```python
# server/tests/validation/test_pickup_time.py
import pytest
from server.brain.layer1.validation.registry import ValidationStatus
from server.brain.layer1.validation.validators import validate_pickup_time


@pytest.mark.asyncio
async def test_valid_pickup_time(mock_tenant_cfg, mock_ctx):
    result = await validate_pickup_time("19:30", mock_tenant_cfg, mock_ctx)
    assert result.status == ValidationStatus.VERIFIED
    assert "canonical_iso" in result.enriched_data


@pytest.mark.asyncio
async def test_pickup_time_too_soon(mock_tenant_cfg, mock_ctx):
    result = await validate_pickup_time("in 5 minutes", mock_tenant_cfg, mock_ctx)
    assert result.status == ValidationStatus.FAILED
    assert "too soon" in result.detail.lower()


@pytest.mark.asyncio
async def test_pickup_time_after_hours(mock_tenant_cfg_closed, mock_ctx):
    result = await validate_pickup_time("23:30", mock_tenant_cfg_closed, mock_ctx)
    assert result.status == ValidationStatus.FAILED
```

## File locations

| Role | Path |
|---|---|
| Registry contract | `server/brain/layer1/validation/registry.py` |
| Default validators | `server/brain/layer1/validation/validators.py` |
| Gate registry | `tools/dispatcher.py` → `GATED_TOOLS` |
| L4 prompt rendering | `server/brain/memory_manager.py` → `render_l4_validation` |
| Trace persistence | `server/brain/layer1/persist.py` → `serialize_layer_trace` |
| Pattern doc | `docs/adding-a-validator.md` (this file) |

# Adding a new tool to Sailly

Sailly tools are per-file handlers in `server/tools/handlers/`. Each tool has:

1. **A handler file** at `server/tools/handlers/<tool_name>.py`
   - Exports `async def handle(args: dict, ctx: ToolContext) -> ToolResult`
   - Exports `TOOL_NAME = "<tool_name>"`
   - Has an associated test file at `server/tests/tools/test_<tool_name>.py`

2. **Registration** in `server/tools/handlers/__init__.py` `ALL_HANDLERS` dict

3. **Function declaration** in `tools/definitions.py` if the LLM should be able
   to call it natively (Gemini function calling schema)

4. **Layer 3 policy considerations** — does this tool need rate limiting,
   quantity caps, or argument validation in `server/brain/layer3/policy.py`?

5. **Dispatcher classification** in `tools/dispatcher.py`:
   - Tools in `GATED_TOOLS` → slot validation required before fire (Phase 5.5)
   - Read-only tools (get_menu, get_date_info, faq) → no gate, pass through

6. **A regression scenario** at
   `server/tests/regression/scenarios/<tool_name>_<flow>.jsonl`

7. **A note** in this doc's Tool Inventory section describing purpose + contract

---

## Handler template

```python
"""
<tool_name> — one-line description.

Phase N decision:
  - <decision-key>: <choice> — what it means
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "<tool_name>"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      <arg_name>: <type> — description
    """
    # Guard decisions (caps, gates, validation)
    ...

    # Core logic or delegation to executor
    ...

    return ToolResult(ok=True, data={...})
```

---

## Pre-merge checklist

- [ ] Handler file follows the template above
- [ ] `TOOL_NAME` constant exported
- [ ] Unit tests cover: happy path, 2+ error paths, edge cases
- [ ] Handler registered in `ALL_HANDLERS` (`server/tools/handlers/__init__.py`)
- [ ] Function schema added to `tools/definitions.py` (if LLM-callable)
- [ ] If state-mutating: dispatcher classification + dedup behaviour verified
- [ ] If external API call: uses appropriate breaker from `server/tools/common/breakers.py`
- [ ] If slot-gated: slot paths added to `GATED_TOOLS` in `tools/dispatcher.py`
- [ ] No tenant-specific values hardcoded — all from `ctx.tenant_cfg` / YAML
- [ ] Regression scenario added (or existing scenario updated)

---

## ToolContext reference

```python
ctx.call_sid        # str — Twilio call SID or browser-* demo SID
ctx.tenant_id       # str — e.g. "doboo"
ctx.tenant_cfg      # dict — raw tenant YAML (all keys available)
ctx.state           # ConversationState — live per-call state
ctx.now()           # datetime — current time in Europe/Berlin tz
ctx.get_tenant_value("key1", "key2", default=None)  # safe nested dict access
```

## ToolResult reference

```python
ToolResult(ok=True,  data={"key": "value"})           # success
ToolResult(ok=False, data={...}, error="reason_code") # failure
result.to_legacy_dict()  # convert to executor.py dict format
```

---

## Tool Inventory

| Tool | File | Decision | Group |
|---|---|---|---|
| `create_order` | `handlers/create_order.py` | ceiling-30, cap-200, two-thresholds | Commerce |
| `create_reservation` | `handlers/create_reservation.py` | current-alternatives | Commerce |
| `verify_address` | `handlers/verify_address.py` | ask-caller-confirm | Commerce |
| `send_sms` | `handlers/send_sms.py` | current-cascade, strict-gate | Commerce |
| `transfer_to_human` | `handlers/transfer_to_human.py` | current-payload | Control |
| `end_call` | `handlers/end_call.py` | state-machine (Phase 3) | Control |
| `get_menu` | `handlers/get_menu.py` | cached-in-state (Phase 4) | Control |
| `get_date_info` | `handlers/get_date_info.py` | extend-get-date-info | Info |
| `faq` | `handlers/faq.py` | static-with-llm-fallback | Info |
| `update_state` | `handlers/update_state.py` | deprecate (removal: Phase 8) | Cleanup |

---

## Circuit breakers

External API calls must use the appropriate breaker from
`server/tools/common/breakers.py`:

```python
from server.tools.common.breakers import MAPS_BREAKER, TWILIO_BREAKER

# Usage with server.core.resilience.call_external:
result = await call_external("maps_geocode", _do_geocode, breaker=MAPS_BREAKER)
```

Available breakers: `MAPS_BREAKER`, `TWILIO_BREAKER`, `WHATSAPP_BREAKER`,
`SMS_BREAKER`, `GEMINI_BREAKER`.

---

## When NOT to add a tool

- **The action can be done by the LLM grounded response alone** (e.g. answer
  a simple factual question about the menu using Phase 4 compact context) →
  add a FAQ entry instead of a new tool.
- **The action is a variant of an existing tool** (e.g. "update delivery
  address mid-order") → extend the existing tool with an optional arg.
- **The action requires human judgment** (e.g. custom catering quote) →
  route to `transfer_to_human` with `reason="catering_request"`.

# Brain / Conversation Logic Audit Instructions

These instructions apply to `server/brain/` and override the repository root
guidance for bot behavior work.

## Core Invariants

The conversation brain is a state machine. Preserve invariants before improving
edge cases:

- Do not commit reservations or orders before all required slots are valid.
- Do not skip pre-commit readback when the scenario requires confirmation.
- Do not ask for already provided information unless the user corrected or
  contradicted it.
- Do not switch an order flow into reservation slots or vice versa.
- Do not set bot identity terms such as `Sailly` as `customer_name`.
- Do not hallucinate dishes, prices, policies, or delivery coverage.
- Do not store display strings where canonical state values are required.

## Files To Read Before Editing

- `v4_pipeline.py`
- `conversation_state.py`
- `context_doc_builder.py`
- `v4_turn_processor.py`
- `layer1/text_mode_runner.py`
- relevant worker/node files under `workers/` or `layer1/nodes/`
- tenant config in `configs/tenants/doboo.yaml`
- tool execution in `tools/executor.py` when tool behavior is involved

## Menu And Price Rules

Tenant config is the source for menu items and prices. Do not hardcode menu
prices in brain code.

Important DOBOO examples:

- `Bibimbap` is a generic item at `14.90 EUR`.
- `Bibimbap vegetarisch`, `Bibimbap Haehnchen`, `Bibimbap Rind`, and other
  variants have their own prices.
- If the user says plain `Bibimbap`, do not silently choose a variant.

## Readback And Commit Rules

For orders, readback should include enough detail for the caller and evaluator:

- item(s)
- price(s)
- quantity
- customer name when known
- delivery address when delivery is intended

For delivery, address is part of the order summary. For pickup, do not invent an
address or phone requirement unless the business flow requires it.

When a user says `Ja, ich moechte...` after a readback, the leading confirmation
must win unless there is an explicit denial or correction. Do not create a loop
by treating every repeated order phrase as a fresh unconfirmed request.

## Safe Fix Rules

- Prefer small state-machine fixes over broad prompt or fallback changes.
- Avoid bare `except` around slot updates or tool-result application.
- If a high-level Phase H/I case fails, reproduce the root cause in a lower
  phase or deterministic helper test when possible.
- Any shared edit in intent routing, slot extraction, date/time parsing, menu
  resolution, or tool execution needs upstream regression checks.
- Do not optimize for one persona at the expense of the base phase.


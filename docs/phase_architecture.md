# Phase A-I Validation Architecture

This document explains the validation ladder Codex must use when auditing or
fixing Sailly. Phases A-I are progressive. Later phases stress invariants that
earlier phases establish.

## Layer 0: Harness And Evidence Certification

Before judging bot behavior, audit the verifier:

- runtime contract: port `8080`, canonical `/health`, websocket
  `ws://127.0.0.1:8080/ws/headless`
- Postgres on `5432` as authoritative transcript/call evidence
- Redis on `6379` for runtime/session state
- `/tmp/scenario_validation/` as derived result artifacts only
- scorer regexes and LLM judge prompts
- duplicate/stale batch files
- force-advance behavior
- known-issues advice freshness

If Layer 0 is wrong, product conclusions may be invalid.

## Phase A: Foundation

Purpose: base reservation and FAQ invariants.

Representative invariants:

- detect reservation intent
- capture party size, date, time, and name
- resolve German relative dates and times
- answer basic FAQ and menu questions
- handle allergen/AI identity questions honestly

Shared date/time, FAQ, or slot extraction edits must recheck Phase A.

## Phase B: Ordering And Delivery

Purpose: single-intent order correctness.

Representative invariants:

- takeaway order capture
- multi-item order capture
- correction handling
- delivery address capture and correction
- out-of-zone handling
- order commit and readback
- menu item and price resolution

Menu, readback, order state, address, and create-order edits must recheck
Phase B first.

## Phase C: Multi-Intent Composition

Purpose: combine multiple goals in one call.

Representative invariants:

- order plus question
- reservation plus order
- long input extraction
- indecision and corrections
- mid-response interruption

Intent routing and state-machine edits must recheck Phase C.

## Phase D: Stress And Edge Robustness

Purpose: robustness under difficult caller behavior.

Representative invariants:

- silence handling
- rude caller handling
- unrealistic orders
- chaotic indecision
- long call handling
- after-hours handling
- escalation rather than loops

Do not weaken normal A-C flows to satisfy D edge cases.

## Phase F: Late And Urgent Calls

Purpose: time-sensitive reservations, orders, and hours questions.

Representative invariants:

- opening-hours answer before order
- urgent reservation
- hours plus order combo
- next-day reservation
- time-sensitive pickup
- callback with reservation intent

Date/time availability and callback edits need Phase F checks.

## Phase G: Advanced Multi-Intent Chains

Purpose: state transitions across multiple intents.

Representative invariants:

- FAQ then order
- reservation plus menu price question
- delivery switched to pickup
- corrected delivery address
- complaint then reservation
- reservation, order, and FAQ in one call

Intent-router, slot, and active-intent stack edits need Phase G checks.

## Phase H: Negative And Safety Behavior

Purpose: boundaries, complaints, escalation, and safety.

Representative invariants:

- AI identity honesty
- off-topic redirection
- complaint handling
- discount policy without false promise
- German response even after English prompt
- manager/escalation handling
- competitor question handling

For H failures, distinguish product bugs from caller-bot drift and scorer false
positives before editing product code.

## Phase I: Complex Voice-Agent Edge Cases

Purpose: top-of-pyramid voice-agent behaviors.

Representative invariants:

- rambling caller patience and extraction
- connection issues without re-asking clearly provided info
- dietary question without invented allergen facts
- billing dispute escalation
- long silence without loops or immediate hangup

If an I failure appears, first ask whether the same root cause can be reproduced
in a lower phase or deterministic helper test. Avoid broad E2E-driven patches.

## Edit Impact Rule

Every fix plan must include:

- affected phase(s)
- upstream invariants at risk
- downstream edge cases to recheck
- exact validation command

Example:

```text
Edit: order readback construction in v4_pipeline.py
Affected: B ordering, G delivery-to-pickup, I connection issues
Upstream risk: B1/B2 commit semantics and menu price resolution
Required checks: B1.2_D2, B2.2_D3, I1.2_D4
```


# Regression Harness — Sailly Test Framework

This harness replays caller scenarios against a running Sailly instance and verifies
specific bot behaviors.

## Adding a new scenario

1. Create a `.yaml` file in `scenarios/` with this structure:

```yaml
name: my_scenario_name
description: "What this tests — e.g., bot handles pizza request gracefully"
turns:
  - user: "Hallo, ich hätte gerne eine Pizza."
    expect_contains: ["pizza", "angebot", "empfehlung"]  # bot must mention at least one
    expect_tools: []                                     # no tools should fire
  - user: "Okay, dann einen Bulgogi."
    expect_tools: ["create_order"]
```

2. Run the harness:
```bash
cd /home/charles2/sailly-browser-demo
python -m server.tests.regression.harness
```

Or run a single scenario:
```bash
python -m server.tests.regression.harness --only my_scenario_name
```

## Scenario design

- **name**: unique ID for the scenario (used in reports, must be valid Python identifier)
- **description**: human-readable intent (what behaviour does this verify?)
- **turns**: list of user utterances + assertions
  - **user**: what the caller says
  - **expect_contains**: list of substrings that should appear in bot response (case-insensitive)
  - **expect_tools**: tools that must fire during this turn

## Universal assertions (applied to all scenarios)

Every scenario automatically checks:
- No forbidden phrases (e.g., "technisches Problem", "[tool:", etc.)
- Minimum response length (20 chars)
- Maximum turn latency (12 seconds)

These catch regressions that break the guardrails globally.

## Viewing results

- **Console output**: Pass/fail per scenario, with check details
- **JSON output**: Full results with all bot responses and tool calls
```bash
python -m server.tests.regression.harness --json-output /tmp/results.json
```

## For Phase 2+

Phase 2 (State migration) and Phase 3 (Brain refactor) will add scenarios here to verify
that migrations preserve behaviour:
- Multi-intent ordering (Philipp stress test)
- Reservation flow
- FAQ handling
- Error recovery
- Barge-in edge cases

See [`02-data-flow.md`](../../mnt/user-data/outputs/architecture-review/02-data-flow.md) for
the canonical turn flow that all scenarios exercise.

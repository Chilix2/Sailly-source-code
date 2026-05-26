# Builder Lab Validation Scaffolding

Builder Lab treats scenarios as capability evidence, not as ad-hoc test files.
The scaffolding in `server/builder/scenario_promotion.py` keeps this explicit
without running any long or destructive tests.

## Sources

- Capability requirements come from `configs/industry_packs/*.yaml`.
- Builder scenarios come from `configs/scenarios/{industry}/{capability}/*.yaml`.
- Legacy caller-bot scenarios are still listed from
  `test-infra/caller-bot-v4/scenarios`.
- Regression harness results can be attached later with
  `update_run_record_from_regression_result(...)`.

## Requirement Shape

Each scenario resolves to:

- `industry` and `capability`
- required and optional tools from the capability pack
- required slots from the capability pack and required tools
- expected tools from the scenario, falling back to required capability tools
- required data keys declared by the scenario
- canonical capability scenario IDs from the industry pack

This lets Builder show what a scenario is supposed to prove before any harness
execution starts.

## Promotion Gates

The lifecycle is deliberately simple:

- `draft`: scenario has an ID, description, caller goal, and an expected outcome.
- `validate`: a completed run exists, expected tools were seen, and assertions passed.
- `publish`: draft is ready and validation passed.

Queued Builder run records now include `requirements` and `promotion_gates`.
The run record remains non-executing until a caller-bot or regression harness
attaches real evidence.

## Safe API Surface

- `GET /api/builder/scenarios/{scenario_id}/requirements` returns requirements
  and current gates without creating a run.
- `POST /api/builder/scenarios/{scenario_id}/run` creates a queued run record
  with requirements and gates, but does not execute the scenario.
- `GET /api/builder/scenarios/runs/{run_id}` returns the stored run record.

This makes the draft -> validate -> publish state machine visible while keeping
actual validation execution opt-in.

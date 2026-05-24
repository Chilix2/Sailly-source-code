# Builder Gap Matrix

Status legend:

- `HAVE (data-driven)`: already configurable through YAML/DB/files; Builder mainly needs UI, validation, and lifecycle.
- `HAVE (code-bound)`: exists in Python/TS but is hardcoded; must be lifted into config to become builder-editable.
- `PARTIAL`: exists for one path, one tenant, or as a non-runtime/stub feature.
- `MISSING`: does not exist in a production-ready form.

Priority legend:

- `Required`: needed for a production-ready Vapi-class builder.
- `Soon`: important after the core builder works.
- `Later`: useful parity feature but not required for initial production readiness.

## Core Mapping

| Vapi primitive | Sailly equivalent | Status | Refactor/build note | Priority |
|---|---|---:|---|---:|
| Assistant object | Tenant YAML in `configs/tenants/*.yaml` plus runtime in `server/main.py` and `server/brain/*` | PARTIAL | Create a single tenant assistant schema that references graph, providers, tools, channels, observability, and deploy status. | Required |
| Assistant first message | `greeting_line`, `ai_disclosure_text`, and hardcoded greeting behavior | PARTIAL | Normalize first-message config and make first-message mode explicit: speak first, wait, or generated. | Required |
| Assistant system prompt | `system_prompt` in tenant YAML plus v4 `ContextDocument` and `TinyGenerator` prompts | PARTIAL | Define prompt layers: tenant global prompt, node prompt, tool guard prompt, generator style prompt. | Required |
| Conversation node prompt | Legacy `server/brain/layer1/nodes/*` prompts; v4 context/generator prompts | HAVE (code-bound) | Add `graph.nodes[].prompt` and hydrate v4 context/generator from config overrides. | Required |
| Conversation node first message | Not a first-class per-node concept in v4 | MISSING | Add `graph.nodes[].first_message` with rules for whether it is spoken on node entry. | Soon |
| Node type: conversation | v4 worker/profile plus legacy node definitions | PARTIAL | Model v4 profile/node as data with type `conversation`; keep worker implementation code behind it. | Required |
| Node type: API request | Python tools/handlers in `tools/executor.py`, `server/tools/handlers/*` | PARTIAL | Add generic HTTP tool schema and execution adapter with credentials, timeout, retry, response mapping. | Required |
| Node type: transfer call | `transfer_to_human` tool/handler | HAVE (code-bound) | Promote transfer into first-class node/tool config with transfer plan, summary, and allowed destinations. | Required |
| Node type: end call | `end_call` tool/handler and v4 end-call stage | HAVE (code-bound) | Promote end-call behavior into graph node plus guarded terminal edge. | Required |
| Node type: global node | FAQ/escalation interrupts, legacy push/return concepts | PARTIAL | Add `graph.global_nodes[]` with enter conditions, priority, and return/terminal behavior. | Required |
| Workflow graph topology | `v4_pipeline.py`, `intent_classifier.py`, `worker_router.py` | HAVE (code-bound) | P0/P1: dual-read graph config with code defaults; P2/P3: make config source of truth. | Required |
| Workflow edge condition | Regex/state routing in `intent_classifier.py`, `worker_router.py` | HAVE (code-bound) | Define deterministic edge conditions as config: intents, keywords, slots, state predicates; optional LLM-condition edge later. | Required |
| Blank edge / auto-advance | Some v4 commit/generator flow is implicit | HAVE (code-bound) | Add `graph.edges[].auto_advance` for deterministic sequential steps. | Soon |
| Natural-language LLM edge condition | No generic runtime equivalent | MISSING | Optional edge type evaluated by LLM behind strict fallback and regression gates. Do not replace deterministic routing by default. | Later |
| Variable extraction | `ConversationState`, workers, slot extraction, commit slots | HAVE (code-bound) | Add `graph.nodes[].variables[]` typed declarations mapped to `ConversationState` fields and extraction workers. | Required |
| Liquid templating | Tenant YAML has prompt text but no general Liquid layer | MISSING | Add safe templating for prompts/tool payloads using declared variables. | Soon |
| Structured outputs | Call reports/auditors exist; not generic assistant config | PARTIAL | Add post-call output schemas and map results into metrics/report artifacts. | Soon |
| Transcriber provider/model | Tenant `audio.stt_model`, Deepgram/Flux registry | PARTIAL | Extend `audio` schema to provider/model/keywords/endpointing; ensure runtime adapter exists for each selectable provider. | Required |
| STT keyword/keyterm boosting | Keyterm loader and Deepgram settings | PARTIAL | Make keywords declared per tenant/node/industry and visible in Builder. | Soon |
| Turn taking / endpointing | `server/main.py` VAD/SmartTurn/Silero constants and `audio` partial fields | PARTIAL | Lift VAD, endpointing, interruption, and silence values into validated tenant config. | Required |
| LLM provider/model | Tenant `model`, provider catalog, `TinyGenerator` hardcoded behavior | PARTIAL | Make v4 generator and worker LLM calls read provider/model/temperature/tool config from tenant assistant schema. | Required |
| TTS provider/voice | Tenant `voice`, `tts.*`, provider catalog, Gemini runtime | PARTIAL | Normalize `tts` schema and implement adapters/validation for each selectable provider. | Required |
| Dynamic variables at call start | Tenant selection and some handshake metadata | PARTIAL | Add call/session `variable_values` input and safe access in prompts/tool payloads. | Soon |
| Built-in tools | `transfer_to_human`, `end_call`, SMS, reservation/order handlers | HAVE (code-bound) | Register built-ins in canonical tool registry with schemas, guards, and UI metadata. | Required |
| Custom HTTP tools | Not production generic | MISSING | Build HTTP tool adapter, credential refs, payload templates, response mapping, test harness. | Required |
| MCP tools | No runtime equivalent | MISSING | Later add MCP tool discovery/execution adapter if needed; not required for first production builder. | Later |
| Tool schemas | Tenant YAML `tools`, `tools/definitions.py`, handler schemas | PARTIAL | Collapse to one canonical tool schema source, generate provider-specific declarations from it. | Required |
| Tool guards | `_GUARDIAN_PRECONDITIONS`, commit gate slot checks | HAVE (code-bound) | Expose guards in Builder as read-only/controlled policies; allow safe tenant-specific optional slots only. | Required |
| Squads / multi-assistant | No first-class equivalent | MISSING | Model as multiple tenant graphs/assistants plus handoff node; build after single-agent graph works. | Later |
| Handoff between assistants | `transfer_to_human` only | PARTIAL | Add assistant/squad handoff destination and context-passing schema. | Later |
| Phone numbers | `twilio_numbers` in tenant YAML and runtime env/Twilio support | PARTIAL | Add phone-number registry, inbound routing, ownership validation, and Builder attach/detach UI. | Required |
| SIP | No verified production equivalent | MISSING | Add only if target customers need SIP; requires telephony routing work. | Later |
| Web voice | `/ws/demo`, `/ws/headless`, dashboard test widget | HAVE (data-driven) | Embed as test-call-from-canvas and production web widget config. | Required |
| Chat | Some dashboard/backend APIs, no full assistant chat channel | MISSING | Add text transport that shares graph/runtime and session persistence. | Soon |
| SMS chat | WhatsApp/SMS env and handlers exist, not unified as chat sessions | PARTIAL | Normalize SMS/WhatsApp channel config and session routing per tenant. | Soon |
| Outbound campaigns | No production campaign manager | MISSING | Later add campaign contacts, schedules, compliance, retry, and analytics. | Later |
| Test call from canvas | `TestCallWidget`, `/ws/headless` | HAVE (data-driven) | Connect selected graph draft/config to test session and capture traces. | Required |
| Evals | Regression harness, browser validation, baselines | HAVE (data-driven) | Unify scenario formats and attach scenario runner to Builder run records. | Required |
| Simulations | Regression harness approximates scripted simulations | PARTIAL | Add AI-caller or scripted caller profiles with pass/fail criteria and iterations. | Soon |
| Scorecards | Auditors and validation scorers | PARTIAL | Turn rubrics into configurable scorecards over structured outputs/metrics. | Soon |
| Boards | Dashboard analytics/monitor pages | PARTIAL | Add Builder-facing boards scoped by tenant/assistant/graph version. | Soon |
| Monitoring | `server/monitoring.py`, Redis list, monitor endpoints | PARTIAL | Add missing config routes and tenant-scoped monitor definitions. | Soon |
| Call logs/debugging | `google_turn_metrics`, admin call viewer, Builder replay | HAVE (data-driven) | Expose deeper columns and graph path/tool payloads in Builder. | Required |
| API/webhook logs | Some tool/error logs, not unified | PARTIAL | Store HTTP tool request/response summaries and webhook delivery logs. | Soon |
| DEV/UAT/PROD environments | No formal environment promotion | MISSING | Add config versions, draft/published states, promotion gates, secrets separation. | Required |
| Config as code | Backend git for YAML/code; dashboard not in git | PARTIAL | Put live dashboard source under git and version tenant graph/config changes. | Required |
| Deployment/publish | Runtime registry has guarded metadata; systemd manual deploy | PARTIAL | Add publish workflow: validate, run regression/evals, write config, reload safe services. | Required |
| Secrets/credentials | Env vars in systemd and local files | PARTIAL | Add credential registry/ref model; never store secrets in tenant graph YAML. | Required |

## Code-Bound Refactor Checklist

These are the highest-impact lifts from Python/TS into config.

| Code-bound area | Current source | Refactor needed |
|---|---|---|
| v4 routing graph | `server/brain/intent_classifier.py`, `server/brain/worker_router.py`, `server/brain/v4_pipeline.py` | Add `graph.nodes` and `graph.edges` config with deterministic conditions; runtime dual-reads config overrides. |
| Worker profiles | `server/brain/worker_router.py`, `server/brain/workers/*` | Define profile metadata in config: id, label, timeout, inputs, outputs, tools, variables, guard class. |
| Commit slots | `server/brain/context_doc_builder.py` | Move slot declarations into guarded config with code defaults and read-only required base guards. |
| Tool registry | `tools/definitions.py`, tenant YAML `tools`, `server/tools/handlers/*` | Create canonical registry that generates LLM schemas, Builder forms, and executor validation. |
| Tool preconditions | `tools/executor.py` | Expose as guard policies attached to tools/nodes; do not let UI silently remove production guards. |
| Generator config | `server/brain/tiny_generator.py` | Read model/provider/style/temperature from assistant config with safe defaults. |
| TTS styles | `server/brain/tts_conditioning.py` | Split tenant-editable voice/style from non-editable safety/persona policy. |
| Turn-taking | `server/main.py` | Move endpointing/VAD/barge-in parameters into validated tenant runtime config. |
| Workflow canvas | dashboard `WorkflowBuilderCanvas.tsx` | Persist/load graph drafts via Builder API and validate them against runtime schema. |

## Missing Production-Ready Pieces

| Missing piece | Why required | Build note |
|---|---|---|
| Runtime graph config schema | Without it, drag/drop cannot change live behavior | Define schema, migrations, validators, dual-read runtime. |
| Graph draft/publish lifecycle | Non-developers need safe editing without breaking live calls | Draft, validate, test, publish, rollback. |
| Unified scenario runner | Current Builder run record is not full execution | Attach regression/browser/headless runner and persist results. |
| Generic HTTP tools | Vapi-class builders need user-defined API calls | Build adapter with credentials, payload templates, response mapping, logs. |
| Environment promotion | Production-ready requires DEV/UAT/PROD safety | Add graph versions, environment labels, promotion gates. |
| Credential registry | Provider/tool secrets cannot live in graph YAML | Store refs and resolve from env/secret manager. |
| Dashboard version control | Current live dashboard source is not in git | Restore git repo or define deployment source of truth. |

## Strategic Read

Sailly has more deterministic safety than Vapi-style natural-language routing: commit gates, GUARDIAN preconditions, and regression harnesses. The Builder should expose those as first-class visual constraints. The goal is not to replace Sailly’s deterministic core with Vapi’s LLM edge router; the goal is to make Sailly’s deterministic graph configurable, testable, and publishable by non-developers.

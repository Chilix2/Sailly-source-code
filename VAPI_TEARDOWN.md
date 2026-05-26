# Vapi Teardown

This document models Vapi as a set of builder primitives. Sailly should not adopt Vapi internally; the value is understanding the UX/config completeness that a non-developer expects from a Vapi-class voice-agent builder.

## Source Links

Primary Vapi documentation consulted:

- Workflows overview: https://docs.vapi.ai/workflows/overview
- Workflows quickstart: https://docs.vapi.ai/workflows/quickstart
- Workflow examples: https://docs.vapi.ai/workflows/examples
- Assistants quickstart: https://docs.vapi.ai/assistants/quickstart
- Assistant API schema: https://docs.vapi.ai/api-reference/assistants/create
- Assistant dynamic variables: https://docs.vapi.ai/assistants/dynamic-variables
- Structured outputs: https://docs.vapi.ai/assistants/structured-outputs-quickstart
- Tools: https://docs.vapi.ai/tools
- Custom tools: https://docs.vapi.ai/tools/custom-tools
- MCP tools: https://docs.vapi.ai/tools/mcp
- Squads: https://docs.vapi.ai/squads
- Handoff: https://docs.vapi.ai/squads/handoff
- Calls API: https://docs.vapi.ai/api-reference/calls/create
- Web SDK: https://docs.vapi.ai/quickstart/web
- Chat: https://docs.vapi.ai/chat/quickstart
- SMS chat: https://docs.vapi.ai/chat/sms-chat
- SIP: https://docs.vapi.ai/advanced/sip
- Outbound campaigns: https://docs.vapi.ai/outbound-campaigns/quickstart
- Server URLs and webhooks: https://docs.vapi.ai/server-url/setting-server-urls
- Local webhook forwarding: https://docs.vapi.ai/server-url/developing-locally
- Debugging: https://docs.vapi.ai/debugging
- Evals: https://docs.vapi.ai/observability/evals-quickstart
- Simulations: https://docs.vapi.ai/observability/simulations-quickstart
- Scorecards: https://docs.vapi.ai/observability/scorecard-quickstart
- Boards: https://docs.vapi.ai/observability/boards-quickstart
- Monitoring: https://docs.vapi.ai/observability/monitoring-quickstart
- Enterprise environments: https://docs.vapi.ai/documentation/best-practices/enterprise-environments-dev-uat-prod

## Core Object Model

| Vapi object | What it represents | Builder meaning |
|---|---|---|
| `Assistant` | The primary voice/chat agent configuration | One configurable agent with transcriber, model, voice, prompts, tools, messages, hooks, and observability plans. |
| `Workflow` | A visual flow of nodes and edges | Canvas-based deterministic control flow. Vapi docs now indicate Workflows are not recommended for new builds compared with Assistants/Squads, but the workflow model remains instructive for visual builders. |
| `WorkflowNode` | A step in a workflow | Conversation, API request, transfer, end-call, tool/control, or global interrupt node. |
| `WorkflowEdge` | Transition between nodes | Natural-language condition or blank auto-advance. |
| `Tool` | An action the assistant can invoke | Built-in, custom HTTP function, code/integration tool, MCP tool, transfer/end/DTMF/SMS/voicemail/handoff. |
| `Squad` | Multi-assistant group | Several assistants with handoff between them. |
| `HandoffTool` | Transfer between assistants/squads | Tool-call transition with context/variable passing. |
| `Call` | Voice runtime execution | Phone/web/SIP/outbound voice session using an assistant/squad/workflow. |
| `Chat` / `Session` | Text or SMS runtime execution | Multi-turn chat transport, including SMS sessions. |
| `PhoneNumber` | Telephony endpoint | Inbound/outbound number assigned to assistant/squad/server URL. |
| `OutboundCampaign` | Batch outbound calls | Campaign over CSV/contact list and an assistant. |
| `Eval` | Deterministic test case | Mock conversation with assertions. |
| `Simulation` | AI caller test | Voice/chat AI-caller test with criteria and iterations. |
| `Scorecard` | Post-call scoring | Quality scoring over structured outputs. |
| `Board` | Analytics dashboard | Custom reporting over calls/cost/outcomes. |
| `Monitor` | Scheduled insight/check | Scheduled analytics that opens issues/notifications. |

## Workflow Node Types

Vapi’s workflow builder centers on the following node classes:

| Node type | Conversational? | Purpose |
|---|---:|---|
| Conversation node | Yes | Prompt the user, speak a first message, extract variables, and decide where to route next. |
| API Request node | No/control | Make an HTTP request and use the response downstream. |
| Transfer Call node | Control + spoken transition | Transfer to a human/number/SIP destination; may include summary/transfer plan. |
| End Call node | Control | End the call with optional final message. |
| Tool node | Control/action | Invoke a configured tool from the workflow. |
| Global node | Usually conversational | Reachable from anywhere when its enter condition matches; used for interruptions like FAQ/escalation. |
| Say/Gather-style behavior | Conversational/control | Speak, collect, then continue; in Vapi this is usually represented through conversation node prompts/variables/edges rather than a separate low-level telephony primitive. |

Important distinction: Vapi separates conversational nodes from control-flow/action nodes. A mature Sailly builder should do the same, even if internally we still execute many actions as tools.

## Edges And Transitions

Vapi workflow edges are:

- Directed transitions from one node to another.
- Guarded by natural-language conditions such as “user wants to book an appointment”.
- Allowed to be blank, meaning auto-advance.
- Used by global nodes as enter conditions that can match from anywhere.

This is different from Sailly’s current v4 routing, which is deterministic Python regex/state logic. Vapi optimizes for no-code natural-language routing; Sailly currently optimizes for predictability, auditability, and regression testing.

## Variables And Extraction

Vapi has several variable/extraction mechanisms:

| Mechanism | Description | Runtime use |
|---|---|---|
| Workflow `extractVariables` | Conversation nodes define typed variables to capture | Downstream edge conditions, prompts, API payloads |
| Liquid variables | `{{first_name}}`, `{{transport.conversationType}}`, nested/array access | Prompts, messages, server payloads |
| Assistant override variables | Values passed at call/chat start via assistant overrides | Dynamic personalization |
| Handoff variable extraction | `variableExtractionPlan` before handoff | Data passed to the destination assistant/squad |
| Structured outputs | Post-call extraction over transcript/messages/tool results | Artifacts, scorecards, analytics |
| Aliases | Derived variables from other variables | Convenience for downstream use |

Variable schemas can include typed object fields, nested objects, arrays, and array-of-object structures. This makes variables a first-class builder concept, not just incidental Python state.

## Assistant Configuration Surface

A Vapi assistant exposes a broad config schema.

### Transcriber

Supported provider families include Deepgram, AssemblyAI, Azure Speech, Google, Gladia, Speechmatics, Talkscriber, OpenAI, Cartesia, Soniox, ElevenLabs, and custom transcribers.

Common knobs:

- Provider
- Model/language
- Endpointing/silence controls
- Confidence threshold
- Formatting/smart formatting
- Keyword/keyterm boosting
- Provider credentials or credential references

### Model / LLM

Supported provider families include Anthropic, Bedrock Anthropic, OpenAI, OpenRouter, Google, Groq, DeepSeek, xAI, Together, Perplexity, Cerebras, DeepInfra, Inflection, Minimax, Anyscale, and custom LLMs.

Common knobs:

- Provider/model
- System messages/prompts
- Temperature/max tokens where supported
- Tools/tool IDs
- Structured output and analysis configuration
- Server/webhook integration

### Voice / TTS

Supported provider families include Azure, Cartesia, Deepgram, ElevenLabs, Hume, LMNT, Neuphonic, OpenAI, PlayHT, Rime, Smallest, Tavus, Vapi, Sesame, Inworld, Minimax, WellSaid, and custom voices.

Common knobs:

- Provider
- Voice ID/name
- Language
- Speaking style/speed options where supported
- Credential references

### Conversation And Runtime Controls

Vapi exposes:

- `firstMessage`
- `firstMessageMode`: assistant speaks first, waits for user, or generates first message
- `firstMessageInterruptionsEnabled`
- `maxDurationSeconds`
- `backgroundSound`
- `voicemailDetection`
- `voicemailMessage`
- `endCallMessage`
- `endCallPhrases`
- `startSpeakingPlan`
- `stopSpeakingPlan`
- `monitorPlan`
- `artifactPlan`
- `analysisPlan`
- `compliancePlan`
- `keypadInputPlan`
- transport configurations

### Messages, Server URL, Webhooks

Vapi emits configurable client/server messages and webhook events:

- Transcripts
- Status updates
- Tool calls
- Transfer/handoff requests
- User interruptions
- End-of-call reports
- Analysis/artifact results

Server URL precedence is important:

1. Tool/function server URL
2. Assistant server URL
3. Phone-number server URL
4. Organization/account URL

This lets builders override routing at the narrowest relevant level.

## Tools

Vapi’s tool model includes:

| Tool type | Description |
|---|---|
| Built-in transfer | Transfer to phone/SIP/human destinations |
| Built-in end call | End conversation deliberately |
| DTMF/keypad | Send or collect keypad input |
| SMS/voicemail-related tools | Channel-specific actions |
| Custom HTTP function | JSON Schema function with server URL and response |
| Code/integration tools | Hosted/integration-backed actions |
| MCP tools | Tools discovered from MCP server at call/chat start |
| Handoff tool | Transition to assistant/squad with context/variables |

Custom tools define a function name, description, JSON Schema parameters, and server URL. Tool server auth is meant to use credential references rather than inline secrets.

MCP tools connect to an MCP server over Streamable HTTP by default. Vapi fetches tools from that MCP server and dynamically adds them to the assistant for that call/chat.

## Squads And Handoff

Vapi Squads allow multiple assistants to cooperate. Key primitives:

- `Squad` with members
- Entry assistant or default first member
- Persistent assistant members or transient inline assistants
- Handoff tool to assistant or squad destination
- Multiple possible destinations
- Dynamic destination selection via webhook
- Spoken handoff messages
- Context engineering for what gets passed
- Variable extraction before handoff
- Rejection handling

The conceptual difference from Workflows: Workflows route between nodes inside one flow; Squads route between independently configured assistants.

## Channels

| Channel | Vapi primitive | Notes |
|---|---|---|
| PSTN phone | `PhoneNumber`, `Call` | Inbound by assigning assistant/squad/server URL; outbound by creating calls with customer number. |
| SIP | SIP phone number / SIP URI | SIP headers can pass template variables; server URL can resolve assistant dynamically. |
| Web voice | `@vapi-ai/web` SDK | Public key plus `vapi.start(assistantId)`; emits call/transcript events. |
| Chat | `Chat` API | Multi-turn via previous chat ID. |
| SMS chat | SMS sessions | Requires approved/imported Twilio 10DLC number; sessions persist for inactivity window. |
| Outbound campaigns | `OutboundCampaign` | Dashboard batch calling from real provider number and CSV/contact list. |

## Observability And Testing

| Primitive | What it does | Builder expectation |
|---|---|---|
| Call logs | Transcript, messages, tool calls, timings, failures | Debug each call from UI |
| API logs | Request/response/auth diagnostics | Debug backend integrations |
| Webhook logs | Delivery and response timing | Debug server URL/tool callbacks |
| Artifact plan | Recordings, transcripts, logs, structured output IDs, scorecards | Configure what data gets saved |
| Analysis plan | Summary, structured data, success evaluation, outcomes | Configure post-call analysis |
| Structured outputs | Typed post-call extraction | Feed reports/scorecards |
| Scorecards | Metric scoring over structured outputs | Quality measurement |
| Evals | Mock conversations with exact/regex/AI/tool assertions | CI and release gates |
| Simulations | AI-caller tests over chat or voice | Realistic pre-prod validation |
| Boards | Custom dashboards over calls/cost/outcomes | Ops visibility |
| Monitors | Scheduled checks and issue/notification creation | Production monitoring |

Vapi’s debugging lifecycle expects a builder user to move between call logs, API logs, webhook logs, and tool test payloads without leaving the product.

## Lifecycle And Environments

Vapi enterprise guidance recommends:

- Separate DEV, UAT/staging, and PROD environments.
- Config as code.
- Isolated credentials/secrets and RBAC.
- CI promotion from lower to higher environments.
- Eval/simulation gates before production.
- Webhook testing locally through the Vapi CLI and tunnels.

For Sailly, this maps less to adopting Vapi’s system and more to creating a versioned tenant graph/config lifecycle with promotion gates.

## What Vapi’s Builder Actually Gives A Non-Developer

A non-developer can typically:

1. Pick a channel or assistant.
2. Pick transcriber/model/voice providers.
3. Write first message and prompts.
4. Add tools with schemas or integrations.
5. Add variables and dynamic templates.
6. Build a visual workflow or squad.
7. Define routing/handoff/transfer/end behavior.
8. Attach phone/web/chat/SMS/outbound channels.
9. Run test calls, evals, and simulations.
10. Inspect transcripts, tool calls, costs, failures, and scorecards.
11. Promote/deploy with environment separation.

That is the target experience. Sailly can keep deterministic routing and guard layers internally, but the Builder must expose the same completeness: graph, prompts, variables, tools, channels, tests, observability, and deploy lifecycle.

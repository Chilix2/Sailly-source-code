/**
 * Corrected TypeScript types for /api/admin/call/{call_sid}/turns endpoint
 * 
 * This file documents what the API *actually* returns (as of 2026-05-29).
 * Compare with apps/dashboard/types/sailly-debugger.ts to identify gaps.
 * 
 * Key differences from current TurnRow:
 * - ADDED: execution_spans field
 * - ADDED: Phase 9 stage timings (stt_ms, extract_ms, l2_ms, tool_ms)
 * - ADDED: Classification fields (intent, turn_type, worker_profile)
 * - CHANGED: layer1_decision and layer3_changes are JSON STRINGS (not parsed)
 * - REMOVED: Fields never populated by API (id, call_id, call_sid at turn level, vad_*, stage1/2_*, etc.)
 */

// ────────────────────────────────────────────────────────────────────────────
// ExecutionSpan — Trace of one operation within a turn
// ────────────────────────────────────────────────────────────────────────────

export interface ExecutionSpan {
  /**
   * Unique identifier for this span (12-char hex UUID).
   * Unique within a (call_sid, turn_number) pair.
   */
  span_id: string;

  /**
   * Reference to parent span (null if root).
   * Forms a shallow tree hierarchy.
   */
  parent_span_id: string | null;

  /**
   * Execution layer: 1 = Orchestrator, 2 = LLM/Chat, 3 = Policy/Gate
   */
  layer: number;

  /**
   * Operation type: classify | prereq | chat | commit_gate | policy | execute_tool
   */
  operation: string;

  /**
   * Human-readable operation name (e.g., "Intent classification", "LLM response generation")
   */
  name: string | null;

  /**
   * LLM model identifier if Layer 2 (e.g., "gpt-4", "claude-3-opus")
   */
  model: string | null;

  /**
   * Wall-time duration of operation (ms), rounded to 2 decimals.
   * Computed: t_end_ms - t_start_ms
   * Available in response from DB; Python dataclass computes on serialization.
   */
  latency_ms: number;

  /**
   * Time-to-first-token for streaming operations (ms), or null.
   * Only meaningful for Layer 2 (LLM) spans.
   */
  ttft_ms: number | null;

  /**
   * Operation outcome: "ok" | "error" | "blocked"
   */
  status: string;

  /**
   * Input token count for Layer 2 operations, null otherwise.
   */
  tokens_in: number | null;

  /**
   * Output token count for Layer 2 operations, null otherwise.
   */
  tokens_out: number | null;

  /**
   * LLM stop reason if Layer 2: "stop" | "length" | "error" | etc., or null.
   */
  finish_reason: string | null;

  /**
   * Variable payload (JSONB in database).
   * Contents depend on operation type:
   * - Layer 1 (classify): may include prompt_template, confidence
   * - Layer 2 (chat): may include prompt_template, temperature, context_tokens
   * - Layer 3 (policy): may include policy_rules_checked, policy_pass, violations
   */
  io: Record<string, unknown>;
}

// ────────────────────────────────────────────────────────────────────────────
// TurnRow (CORRECTED) — Turn metrics with execution spans
// ────────────────────────────────────────────────────────────────────────────

/**
 * Corrected TurnRow type matching /api/admin/call/{call_sid}/turns response.
 * 
 * NOTE: This differs from apps/dashboard/types/sailly-debugger.ts
 * which includes extra fields never populated by the API.
 * 
 * Use this for actual API response handling.
 */
export interface TurnRowCorrected {
  /**
   * Sequential turn number (1-indexed).
   */
  turn_number: number;

  /**
   * User input (ASR output from STT engine).
   */
  user_text: string | null;

  /**
   * Bot response (generated text sent to TTS).
   */
  bot_text: string | null;

  // ── STT & Confidence ─────────────────────────────────────────────────────

  /**
   * Speech recognition confidence [0.0, 1.0].
   */
  stt_confidence: number | null;

  // ── Latency Metrics ──────────────────────────────────────────────────────

  /**
   * STT latency (audio in → text out).
   * Milliseconds.
   */
  stt_latency_ms: number | null;

  /**
   * LLM latency (tokens in → tokens out).
   * Milliseconds. Corresponds to Layer 2 duration.
   */
  llm_latency_ms: number | null;

  /**
   * Total turn latency (user audio start → bot audio start).
   * Milliseconds.
   */
  total_latency_ms: number | null;

  /**
   * Time-to-first-byte for TTS output.
   * Milliseconds. Phase 9 observability field.
   */
  tts_ttfb_ms: number | null;

  // ── Phase 9 Stage Timings ─────────────────────────────────────────────────
  // Per-stage latency breakdown (Phase 9 observability decision 9.O2)
  // Sum should approximate total_latency_ms (within orchestration overhead)

  /**
   * STT processing time (ms).
   * Phase 9 stage timing.
   */
  stt_ms: number | null;

  /**
   * Slot extraction time (ms).
   * Phase 9 stage timing.
   */
  extract_ms: number | null;

  /**
   * Layer 2 (LLM classification/response) time (ms).
   * Phase 9 stage timing.
   */
  l2_ms: number | null;

  /**
   * Tool execution time (ms).
   * Phase 9 stage timing.
   */
  tool_ms: number | null;

  // ── Tool Execution ────────────────────────────────────────────────────────

  /**
   * Array of tool names called in this turn.
   * e.g., ["create_order", "send_sms"]
   * Parsed from JSON string in database.
   */
  tools_called: string[];

  // ── Classification Context ───────────────────────────────────────────────

  /**
   * FSM node active at end of turn.
   * e.g., "GREETING" | "INFO" | "ORDER" | "RESERVE" | "READBACK" | "COMMITTED"
   */
  node_name: string | null;

  /**
   * Detected user intent (from shadow classifier).
   * e.g., "place_order", "check_reservation", "faq"
   * Phase 0B / Phase 9 field.
   */
  intent: string | null;

  /**
   * Classified turn type (from shadow classifier).
   * e.g., "bot_prompt", "user_response", "repetition"
   * Phase 0B / Phase 9 field.
   */
  turn_type: string | null;

  /**
   * Worker profile for routing context (from shadow classifier).
   * e.g., "order_taker", "support_agent"
   * Phase 0B / Phase 9 field.
   */
  worker_profile: string | null;

  // ── Layer Traces (Observability) ──────────────────────────────────────────
  // Raw JSON strings (not parsed in API; parse in frontend if needed)

  /**
   * Layer 1 (Orchestrator decision) as raw JSON string.
   * Contains FSM node, forced_tools, validators_run.
   * Type hint: JSON string, parse to { node: string; forced_tools: string[]; state_hash: string; validators_run: any[] }
   * 
   * NOTE: TypeScript type in dashboard is Layer1Decision (object), but API returns raw JSON string.
   * Frontend must parse this before accessing properties.
   */
  layer1_decision: string | null;

  /**
   * Layer 2 (LLM raw output) as string.
   * The raw LLM response before policy gate (Layer 3).
   */
  layer2_raw_output: string | null;

  /**
   * Layer 3 (Policy gate changes) as raw JSON string.
   * Contains warnings[], text_changed, tools_changed.
   * Type hint: JSON string, parse to { warnings: any[]; text_changed: boolean; tools_changed: boolean }
   * 
   * NOTE: TypeScript type in dashboard is Layer3Changes (object), but API returns raw JSON string.
   * Frontend must parse this before accessing properties.
   */
  layer3_changes: string | null;

  // ── Text Pipeline & TTS ───────────────────────────────────────────────────

  /**
   * Final text sent to TTS (after policy layer).
   * May differ from layer2_raw_output if policy gate made changes.
   */
  stage3_text: string | null;

  /**
   * TTS adaptive context (situation classification).
   * e.g., "casual_question", "order_confirmation", "error_recovery"
   */
  tts_situation: string | null;

  /**
   * TTS emotional state (mood classification).
   * e.g., "helpful", "apologetic", "enthusiastic"
   */
  tts_mood: string | null;

  /**
   * Validator metrics and breakdown.
   * Structure depends on validators run in this turn.
   * e.g., { slot_confidence: 0.95, flow_stage: "item_selection" }
   */
  validation_breakdown: Record<string, unknown>;

  // ── Metadata & Versioning ────────────────────────────────────────────────

  /**
   * Tenant identifier (e.g., "doboo", "pizzeria_napoli").
   */
  tenant_id: string | null;

  /**
   * Git commit SHA of deployed code that processed this turn.
   */
  build_sha: string | null;

  /**
   * ISO 8601 timestamp when turn was created/recorded.
   */
  created_at: string;

  // ── Execution Traces (Phase 2 Observability) ────────────────────────────

  /**
   * Array of ExecutionSpan objects tracing operations in this turn.
   * 
   * CRITICAL: This field is NOT included in the current TypeScript TurnRow interface.
   * It is always populated by the API (may be empty array if no spans recorded).
   * 
   * Each span records a discrete operation (classify, chat, policy, tool execution, etc.)
   * with timing, status, tokens, and payload data.
   */
  execution_spans: ExecutionSpan[];
}

// ────────────────────────────────────────────────────────────────────────────
// API Response Envelope
// ────────────────────────────────────────────────────────────────────────────

export interface CallTurnsResponseCorrected {
  /**
   * Call session identifier.
   */
  call_sid: string;

  /**
   * Number of turns in this call.
   */
  turn_count: number;

  /**
   * Array of TurnRow objects.
   */
  turns: TurnRowCorrected[];
}

// ────────────────────────────────────────────────────────────────────────────
// Layer Trace Types (for manual parsing of JSON strings)
// ────────────────────────────────────────────────────────────────────────────

export interface ValidatorRun {
  slot: string;
  status: "pending" | "verified" | "failed";
  duration_ms: number;
  retry: number;
}

export interface Layer1Decision {
  node: string;
  forced_tools: string[];
  state_hash: string;
  validators_run: ValidatorRun[];
}

export interface Layer3Changes {
  warnings: Array<{ kind: string; message: string }>;
  text_changed: boolean;
  tools_changed: boolean;
}

// ────────────────────────────────────────────────────────────────────────────
// Usage: Parsing layer1_decision and layer3_changes from JSON strings
// ────────────────────────────────────────────────────────────────────────────

/**
 * Helper to safely parse layer1_decision string into Layer1Decision object.
 * Returns null if parsing fails.
 */
export function parseLayer1Decision(raw: string | null): Layer1Decision | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Layer1Decision;
  } catch {
    return null;
  }
}

/**
 * Helper to safely parse layer3_changes string into Layer3Changes object.
 * Returns null if parsing fails.
 */
export function parseLayer3Changes(raw: string | null): Layer3Changes | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Layer3Changes;
  } catch {
    return null;
  }
}

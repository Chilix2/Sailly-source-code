// Sailly Debugger TypeScript Contracts
// Direct mirrors of Python backend contracts

export type FsmState =
  | "GREETING"
  | "INFO"
  | "ORDER_OR_RESERVE"
  | "READBACK"
  | "COMMITTED"
  | "POST_COMMIT";

export interface ValidatorRun {
  slot: string;
  status: "pending" | "verified" | "failed";
  duration_ms: number;
  retry: number;
}

export interface Layer1Decision {
  node: FsmState | string;
  forced_tools: string[];
  state_hash: string;
  validators_run: ValidatorRun[];
}

export interface Layer3Changes {
  warnings: Array<{ kind: string; message: string }>;
  text_changed: boolean;
  tools_changed: boolean;
}

// Turn row as returned by /api/admin/call/{call_sid}/turns
export interface TurnRow {
  id: number;
  call_id: string;
  call_sid: string;
  tenant_id: string | null;
  turn_number: number;
  user_text: string | null;
  bot_text: string | null;

  // VAD + STT
  vad_start_ms: number | null;
  vad_stop_ms: number | null;
  stt_confidence: number | null;

  // Latencies (TurnTimings)
  stt_latency_ms: number | null;
  llm_latency_ms: number | null;
  tts_latency_ms: number | null;
  tts_ttfb_ms: number | null;
  total_latency_ms: number | null;
  acoustic_gap_ms: number | null;

  // Tools
  tools_called: string[];

  // Layer traces
  node_name: string | null;
  layer1_decision: Layer1Decision | null;
  layer2_raw_output: string | null;
  layer3_changes: Layer3Changes | null;

  // Text pipeline stages
  stage1_clean_text: string | null;
  stage2_clean_text: string | null;
  stage3_text: string | null;

  // Misc
  has_markdown: boolean;
  has_greeting: boolean;
  tts_situation: string | null;
  tts_mood: string | null;
  tts_suppressed_reason: string | null;
  validation_breakdown: Record<string, unknown>;
  build_sha: string | null;
  created_at: string;
}

// Live trace events (Redis append-only)
export type LivePhase =
  | "stt"
  | "extract"
  | "l2"
  | "tool"
  | "tts"
  | "gate"
  | "interrupt"
  | "drop"
  | "checkpoint";

export interface LiveEvent {
  ts: number;
  iso: string;
  phase: LivePhase;
  event: string;
  level: "info" | "warn" | "error";
  detail: unknown;
}

// Session list row
export interface ScenarioTags {
  primary_scenario: string;  // "single_order", "multi_faq", etc.
  scenario_phase: string;    // "A"-"I"
  detected_intents: string[];
  confidence: number;        // 0.0-1.0
  modifiers: string[];       // ["QUICK_COMPLETE", "TRANSFERRED", ...]
  llm_reasoning: string;
  call_sid: string;
  classified_at: string;
}

export interface SessionRow {
  call_sid: string;
  tenant_id: string;
  started_at: string;
  duration_seconds: number;
  turn_count: number;
  ended_properly: boolean;
  build_sha: string;
  // Scenario classification (populated async post-call)
  scenario_tags?: ScenarioTags;
}

// Golden Path
export interface GoldenPath {
  id: string;
  scenario: string;
  description: string;
  turns: Array<{
    turnNumber: number;
    expectedFsmState: FsmState;
    expectedForcedTools?: string[];
    expectedToolsCalled?: string[];
    requiredValidators?: string[];
    forbiddenTools?: string[];
    successCriteria: string;
  }>;
}

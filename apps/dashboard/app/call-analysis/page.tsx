"use client";

import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import {
  Activity,
  RefreshCw,
  Clock,
  AlertTriangle,
  CheckCircle,
  MessageSquare,
  ChevronRight,
  Mic,
  Ear,
  Brain,
  Wrench,
  Shield,
  Volume2,
  Radio,
  Flag,
  FileText,
  Waves,
  ScrollText,
  Loader2,
  User,
  Bot,
  ArrowRight,
  Headphones,
  Play,
  Pause,
  Copy,
  Check,
  Download,
} from "lucide-react";

/* =========================================================================
   Types
   ========================================================================= */

type StageStatus = "ok" | "degraded" | "fail" | "skip";

interface Stage {
  id: string;
  label: string;
  status: StageStatus;
  detail?: string;
}

interface ToolCall {
  name: string;
  arguments?: Record<string, any>;
  result_summary?: string | null;
  duration_ms?: number | null;
  success?: boolean | null;
  error_message?: string | null;
}

interface GuardianEvent {
  content: string;
  timestamp?: string;
}

interface Evaluation {
  scenario?: string | null;
  trajectory_match?: boolean | null;
  failure_patterns?: string | Array<[string, string]> | null;
  verdict?: string | null;
  verdict_reason?: string | null;
  expected_tools?: string | null;
  actual_tools?: string | null;
}

interface TurnData {
  turn_number: number;
  user_text: string | null;
  bot_text: string | null;
  node_name?: string | null;
  latencies: {
    stt_ms: number | null;
    llm_ms: number | null;
    tts_ms: number | null;
    total_ms: number | null;
  };
  stages: Stage[];
  tools: ToolCall[];
  guardian_events: GuardianEvent[];
  evaluation: Evaluation;
  stage_texts: {
    stage1_clean_text: string | null;
    stage2_clean_text: string | null;
    stage3_text: string | null;
  };
  new_metrics?: {
    validation_breakdown: any;
    tts_situation: string | null;
    tts_mood: string | null;
    layer1_decision: any;
    layer2_raw_output: string | null;
    layer3_changes: any;
    stt_confidence: number | null;
  };
}

interface RoadmapData {
  call_sid: string;
  started_at: string | null;
  duration_seconds: number | null;
  quality_score: number | null;
  outcome: string | null;
  was_escalated: boolean | null;
  caller_audio_url?: string | null;
  agent_audio_url?: string | null;
  turns: TurnData[];
}

interface CallSummary {
  call_sid: string;
  started_at: string;
  duration_seconds: number;
  turn_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  issues_count: number;
}

/* =========================================================================
   Helpers
   ========================================================================= */

const STAGE_ICONS: Record<
  string,
  React.ComponentType<{ size?: number; className?: string }>
> = {
  user_input_audio: Mic,
  vad_endpoint: Ear,
  stt_deepgram: FileText,
  brain_context: ScrollText,
  brain_llm_call: Brain,
  brain_tools_emitted: Flag,
  guardian_check: Shield,
  tool_execution: Wrench,
  response_text_final: MessageSquare,
  tts_gemini: Volume2,
  audio_delivery: Radio,
  turn_close: CheckCircle,
};

const STATUS_META: Record<
  StageStatus,
  { label: string; bg: string; text: string; dot: string; border: string }
> = {
  ok: {
    label: "OK",
    bg: "bg-[#f0fdf4]",
    text: "text-[#16a34a]",
    dot: "bg-[#16a34a]",
    border: "border-[#bbf7d0]",
  },
  degraded: {
    label: "Degraded",
    bg: "bg-[#fff8ea]",
    text: "text-brand-peach",
    dot: "bg-brand-peach",
    border: "border-[#fed7aa]",
  },
  fail: {
    label: "Fail",
    bg: "bg-[#fff0ee]",
    text: "text-brand-salmon",
    dot: "bg-brand-salmon",
    border: "border-[#ffc2b4]",
  },
  skip: {
    label: "Skip",
    bg: "bg-brand-cream",
    text: "text-brand-muted",
    dot: "bg-brand-muted",
    border: "border-[#e8d8d2]",
  },
};

function fmtMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms === 0) return "—";
  return `${ms}ms`;
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("de-DE", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

function fmtDuration(secs: number | null | undefined): string {
  if (!secs) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function latencyStatus(
  ms: number | null | undefined,
  goodMax = 800,
  degradedMax = 1500,
): StageStatus {
  if (ms === null || ms === undefined || ms === 0) return "skip";
  if (ms < goodMax) return "ok";
  if (ms < degradedMax) return "degraded";
  return "fail";
}

function parsePatterns(
  raw: Evaluation["failure_patterns"],
): Array<[string, string]> {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw as Array<[string, string]>;
  try {
    const p = JSON.parse(raw);
    return Array.isArray(p) ? p : [];
  } catch {
    return [];
  }
}

function turnOverallStatus(turn: TurnData): StageStatus {
  const statuses = turn.stages.map((s) => s.status);
  if (statuses.includes("fail")) return "fail";
  if (statuses.includes("degraded")) return "degraded";
  return "ok";
}

/* =========================================================================
   UI Building Blocks
   ========================================================================= */

function StatusDot({
  status,
  size = 10,
}: {
  status: StageStatus;
  size?: number;
}) {
  const meta = STATUS_META[status];
  return (
    <span
      aria-label={meta.label}
      className={`inline-block rounded-full ${meta.dot}`}
      style={{
        width: size,
        height: size,
        boxShadow:
          status === "fail" ? "0 0 0 3px rgba(254,150,133,0.20)" : undefined,
      }}
    />
  );
}

function StatusPill({
  status,
  label,
}: {
  status: StageStatus;
  label?: string;
}) {
  const meta = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold ${meta.bg} ${meta.text} border ${meta.border}`}
    >
      <StatusDot status={status} size={7} />
      {label ?? meta.label}
    </span>
  );
}

function StageCard({
  stage,
  index,
  selected,
  onClick,
}: {
  stage: Stage;
  index: number;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = STAGE_ICONS[stage.id] ?? Activity;
  const meta = STATUS_META[stage.status];
  return (
    <button
      onClick={onClick}
      className={`group flex flex-col items-stretch min-w-[132px] rounded-xl border transition-all shadow-sm text-left
        ${
          selected
            ? "bg-white border-brand-pink ring-2 ring-brand-pink/30"
            : "bg-white border-[#e8d8d2] hover:border-brand-pink/50 hover:shadow-md"
        }`}
    >
      <div className="flex items-center justify-between px-3 pt-2.5 pb-1.5">
        <span className="text-[10px] font-bold tracking-widest text-brand-muted uppercase">
          Step {index + 1}
        </span>
        <StatusDot status={stage.status} size={8} />
      </div>
      <div className="flex items-center gap-2 px-3 pb-2.5">
        <span
          className={`flex items-center justify-center w-7 h-7 rounded-lg ${meta.bg} ${meta.text}`}
        >
          <Icon size={14} />
        </span>
        <span className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-brand-navy truncate">
            {stage.label}
          </div>
          {stage.detail ? (
            <div className="text-[10px] text-brand-muted font-mono truncate">
              {stage.detail}
            </div>
          ) : null}
        </span>
      </div>
    </button>
  );
}

function StageConnector({ status }: { status: StageStatus }) {
  const color =
    status === "fail"
      ? "#fe9685"
      : status === "degraded"
        ? "#fec081"
        : status === "ok"
          ? "#16a34a"
          : "#c9b6af";
  return (
    <div
      className="flex items-center justify-center px-1 flex-shrink-0"
      aria-hidden
    >
      <ArrowRight size={14} style={{ color }} />
    </div>
  );
}

/* =========================================================================
   Layer 2 — Stage detail
   ========================================================================= */

function Layer2Panel({
  stage,
  turn,
  selectedSub,
  onSelectSub,
}: {
  stage: Stage;
  turn: TurnData;
  selectedSub: string | null;
  onSelectSub: (id: string | null) => void;
}) {
  const subSteps = useMemo(() => buildSubSteps(stage, turn), [stage, turn]);
  const kpis = useMemo(() => buildKpis(stage, turn), [stage, turn]);
  const meta = STATUS_META[stage.status];
  const Icon = STAGE_ICONS[stage.id] ?? Activity;

  return (
    <div className="bg-white rounded-xl border border-[#e8d8d2] shadow-sm">
      <div className="px-5 py-4 border-b border-[#f5e9e4] flex items-center gap-3">
        <span
          className={`flex items-center justify-center w-9 h-9 rounded-lg ${meta.bg} ${meta.text}`}
        >
          <Icon size={18} />
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-brand-navy">{stage.label}</h3>
            <StatusPill status={stage.status} />
          </div>
          {stage.detail ? (
            <p className="text-xs text-brand-muted font-mono">{stage.detail}</p>
          ) : null}
        </div>
      </div>

      {kpis.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 px-5 py-3 bg-[#fdf5f2] border-b border-[#f5e9e4]">
          {kpis.map((k) => (
            <div
              key={k.label}
              className="bg-white rounded-lg border border-[#e8d8d2] px-3 py-2"
            >
              <div className="text-[10px] uppercase tracking-wide text-brand-muted font-medium">
                {k.label}
              </div>
              <div
                className={`text-sm font-bold mt-0.5 ${k.tone ?? "text-brand-navy"}`}
              >
                {k.value}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="px-5 py-4">
        <div className="text-[10px] font-bold tracking-widest text-brand-muted uppercase mb-2">
          Sub-Steps
        </div>
        {subSteps.length === 0 ? (
          <p className="text-xs text-brand-muted italic">
            No sub-steps recorded for this stage.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {subSteps.map((sub) => {
              const subMeta = STATUS_META[sub.status];
              const active = selectedSub === sub.id;
              return (
                <button
                  key={sub.id}
                  onClick={() => onSelectSub(active ? null : sub.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition
                    ${
                      active
                        ? "bg-brand-cream border-brand-pink ring-2 ring-brand-pink/20"
                        : "bg-white border-[#e8d8d2] hover:border-brand-pink/50"
                    }`}
                >
                  <StatusDot status={sub.status} size={8} />
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-brand-navy truncate max-w-[260px]">
                      {sub.label}
                    </div>
                    {sub.detail ? (
                      <div className="text-[10px] text-brand-muted font-mono truncate max-w-[260px]">
                        {sub.detail}
                      </div>
                    ) : null}
                  </div>
                  <ChevronRight size={12} className="text-brand-muted" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      {selectedSub && (
        <Layer3Panel stage={stage} turn={turn} subId={selectedSub} />
      )}
    </div>
  );
}

function buildKpis(
  stage: Stage,
  turn: TurnData,
): Array<{ label: string; value: string; tone?: string }> {
  const out: Array<{ label: string; value: string; tone?: string }> = [];
  const l = turn.latencies;
  switch (stage.id) {
    case "stt_deepgram":
      out.push({
        label: "Latency",
        value: fmtMs(l.stt_ms),
        tone: latencyToneClass(l.stt_ms, 2500, 4000),
      });
      out.push({
        label: "User text",
        value: turn.user_text ? `${turn.user_text.length} chars` : "—",
      });
      break;
    case "brain_llm_call":
      out.push({
        label: "Latency",
        value: fmtMs(l.llm_ms),
        tone: latencyToneClass(l.llm_ms, 1500, 3000),
      });
      out.push({ label: "Node", value: turn.node_name ?? "—" });
      break;
    case "brain_tools_emitted":
      out.push({
        label: "Expected",
        value: turn.evaluation.expected_tools ?? "—",
      });
      out.push({ label: "Actual", value: turn.evaluation.actual_tools ?? "—" });
      break;
    case "guardian_check":
      out.push({
        label: "Events",
        value: String(turn.guardian_events.length),
        tone: turn.guardian_events.length
          ? "text-brand-salmon"
          : "text-[#16a34a]",
      });
      break;
    case "tool_execution":
      out.push({ label: "Calls", value: String(turn.tools.length) });
      out.push({
        label: "Failed",
        value: String(turn.tools.filter((t) => t.success === false).length),
        tone: turn.tools.some((t) => t.success === false)
          ? "text-brand-salmon"
          : "text-[#16a34a]",
      });
      break;
    case "tts_gemini":
      out.push({
        label: "Latency",
        value: fmtMs(l.tts_ms),
        tone: latencyToneClass(l.tts_ms, 3000, 5000),
      });
      out.push({
        label: "Bot chars",
        value: turn.bot_text ? `${turn.bot_text.length}` : "—",
      });
      break;
    case "turn_close":
      out.push({
        label: "Total",
        value: fmtMs(l.total_ms),
        tone: latencyToneClass(l.total_ms, 2500, 4500),
      });
      out.push({
        label: "Verdict",
        value: turn.evaluation.verdict ?? "—",
        tone: verdictTone(turn.evaluation.verdict),
      });
      break;
  }
  return out;
}

function latencyToneClass(
  ms: number | null | undefined,
  good: number,
  degraded: number,
): string {
  if (ms === null || ms === undefined || ms === 0) return "text-brand-muted";
  if (ms < good) return "text-[#16a34a]";
  if (ms < degraded) return "text-brand-peach";
  return "text-brand-salmon";
}

function verdictTone(v: string | null | undefined): string {
  if (!v) return "text-brand-muted";
  const s = v.toLowerCase();
  if (s.includes("pass") || s === "ok") return "text-[#16a34a]";
  if (s.includes("fail")) return "text-brand-salmon";
  return "text-brand-peach";
}

interface SubStep {
  id: string;
  label: string;
  status: StageStatus;
  detail?: string;
}

function buildSubSteps(stage: Stage, turn: TurnData): SubStep[] {
  const out: SubStep[] = [];
  switch (stage.id) {
    case "stt_deepgram":
      if (turn.user_text) {
        out.push({
          id: "stt_transcript",
          label: "Transcript produced",
          status: "ok",
          detail:
            turn.user_text.slice(0, 60) +
            (turn.user_text.length > 60 ? "…" : ""),
        });
      }
      break;
    case "brain_context":
      if (turn.stage_texts.stage1_clean_text) {
        out.push({
          id: "stage1",
          label: "Stage-1 clean text",
          status: "ok",
          detail: turn.stage_texts.stage1_clean_text.slice(0, 80),
        });
      }
      break;
    case "brain_llm_call":
      if (turn.stage_texts.stage2_clean_text) {
        out.push({
          id: "stage2",
          label: "Stage-2 output",
          status: "ok",
          detail: turn.stage_texts.stage2_clean_text.slice(0, 80),
        });
      }
      break;
    case "brain_tools_emitted":
      turn.tools.forEach((t, i) => {
        out.push({
          id: `emit_${i}`,
          label: `emit: ${t.name}`,
          status: "ok",
          detail: t.arguments
            ? JSON.stringify(t.arguments).slice(0, 80)
            : undefined,
        });
      });
      break;
    case "tool_execution":
      turn.tools.forEach((t, i) => {
        out.push({
          id: `exec_${i}`,
          label: t.name,
          status: t.success === false ? "fail" : "ok",
          detail: t.duration_ms
            ? `${t.duration_ms}ms`
            : (t.result_summary ?? undefined),
        });
      });
      break;
    case "guardian_check":
      turn.guardian_events.forEach((g, i) => {
        out.push({
          id: `guard_${i}`,
          label: `GUARDIAN event #${i + 1}`,
          status: "fail",
          detail: g.content.slice(0, 100),
        });
      });
      break;
    case "response_text_final":
      if (turn.stage_texts.stage3_text) {
        out.push({
          id: "stage3",
          label: "Stage-3 final text",
          status: "ok",
          detail: turn.stage_texts.stage3_text.slice(0, 80),
        });
      }
      break;
    case "turn_close": {
      const patterns = parsePatterns(turn.evaluation.failure_patterns);
      patterns.forEach((p, i) => {
        out.push({
          id: `fp_${i}`,
          label: `${p[0]} ${p[1] ?? ""}`.trim(),
          status: "fail",
          detail: turn.evaluation.verdict_reason ?? undefined,
        });
      });
      if (patterns.length === 0 && turn.evaluation.verdict) {
        out.push({
          id: "verdict",
          label: `Verdict: ${turn.evaluation.verdict}`,
          status: turn.evaluation.verdict?.toLowerCase().includes("fail")
            ? "fail"
            : "ok",
          detail: turn.evaluation.verdict_reason ?? undefined,
        });
      }
      break;
    }
  }
  return out;
}

/* =========================================================================
   Layer 3 — Trace
   ========================================================================= */

function Layer3Panel({
  stage,
  turn,
  subId,
}: {
  stage: Stage;
  turn: TurnData;
  subId: string;
}) {
  const lines = useMemo(
    () => buildTrace(stage, turn, subId),
    [stage, turn, subId],
  );
  return (
    <div className="border-t border-[#f5e9e4] bg-[#fdf5f2] px-5 py-4">
      <div className="text-[10px] font-bold tracking-widest text-brand-muted uppercase mb-2">
        Trace
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[minmax(260px,1fr)_minmax(0,1.5fr)] gap-4">
        <div className="space-y-2">
          {lines.steps.map((s, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="flex flex-col items-center pt-1">
                <StatusDot status={s.status} size={9} />
                {i < lines.steps.length - 1 ? (
                  <div
                    className="w-px flex-1 bg-[#e8d8d2] mt-1"
                    style={{ minHeight: 20 }}
                  />
                ) : null}
              </div>
              <div className="pb-3">
                <div className="text-xs font-semibold text-brand-navy">
                  {s.label}
                </div>
                {s.detail ? (
                  <div className="text-[10px] text-brand-muted mt-0.5">
                    {s.detail}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
        <pre className="bg-white rounded-lg border border-[#e8d8d2] p-3 text-[11px] font-mono text-brand-navy overflow-auto max-h-80 whitespace-pre-wrap">
          {lines.log}
        </pre>
      </div>
    </div>
  );
}

function buildTrace(
  stage: Stage,
  turn: TurnData,
  subId: string,
): { steps: SubStep[]; log: string } {
  const meta = STATUS_META[stage.status];
  // Tool sub-steps
  if (stage.id === "tool_execution" && subId.startsWith("exec_")) {
    const idx = parseInt(subId.split("_")[1], 10);
    const t = turn.tools[idx];
    if (t) {
      return {
        steps: [
          { id: "t0", label: "Tool invoked", status: "ok", detail: t.name },
          { id: "t1", label: "Arguments validated", status: "ok" },
          {
            id: "t2",
            label: "Execution",
            status: t.success === false ? "fail" : "ok",
            detail: t.duration_ms ? `${t.duration_ms}ms` : undefined,
          },
          {
            id: "t3",
            label: "Result",
            status: t.success === false ? "fail" : "ok",
            detail: t.result_summary ?? undefined,
          },
        ],
        log: JSON.stringify(
          {
            tool: t.name,
            arguments: t.arguments ?? {},
            duration_ms: t.duration_ms,
            success: t.success,
            result_summary: t.result_summary,
            error_message: t.error_message,
          },
          null,
          2,
        ),
      };
    }
  }
  if (stage.id === "brain_tools_emitted" && subId.startsWith("emit_")) {
    const idx = parseInt(subId.split("_")[1], 10);
    const t = turn.tools[idx];
    if (t) {
      return {
        steps: [
          {
            id: "e0",
            label: "LLM emitted tool call",
            status: "ok",
            detail: t.name,
          },
          { id: "e1", label: "Arguments", status: "ok" },
        ],
        log: JSON.stringify(
          { name: t.name, arguments: t.arguments ?? {} },
          null,
          2,
        ),
      };
    }
  }
  if (stage.id === "guardian_check" && subId.startsWith("guard_")) {
    const idx = parseInt(subId.split("_")[1], 10);
    const g = turn.guardian_events[idx];
    if (g) {
      return {
        steps: [
          { id: "g0", label: "GUARDIAN rule fired", status: "fail" },
          {
            id: "g1",
            label: "Event recorded",
            status: "fail",
            detail: g.timestamp,
          },
        ],
        log: g.content,
      };
    }
  }
  if (stage.id === "brain_context" && subId === "stage1") {
    return {
      steps: [{ id: "s1", label: "Clean text stage 1", status: "ok" }],
      log: turn.stage_texts.stage1_clean_text ?? "",
    };
  }
  if (stage.id === "brain_llm_call" && subId === "stage2") {
    return {
      steps: [{ id: "s2", label: "Clean text stage 2", status: "ok" }],
      log: turn.stage_texts.stage2_clean_text ?? "",
    };
  }
  if (stage.id === "response_text_final" && subId === "stage3") {
    return {
      steps: [{ id: "s3", label: "Final rendered text", status: "ok" }],
      log: turn.stage_texts.stage3_text ?? "",
    };
  }
  if (stage.id === "turn_close") {
    const patterns = parsePatterns(turn.evaluation.failure_patterns);
    return {
      steps: [
        {
          id: "v0",
          label: "Scenario",
          status: "ok",
          detail: turn.evaluation.scenario ?? "—",
        },
        {
          id: "v1",
          label: "Trajectory match",
          status: turn.evaluation.trajectory_match ? "ok" : "fail",
        },
        {
          id: "v2",
          label: "Verdict",
          status: turn.evaluation.verdict?.toLowerCase().includes("fail")
            ? "fail"
            : "ok",
          detail: turn.evaluation.verdict ?? "—",
        },
      ],
      log: JSON.stringify(
        {
          scenario: turn.evaluation.scenario,
          trajectory_match: turn.evaluation.trajectory_match,
          verdict: turn.evaluation.verdict,
          verdict_reason: turn.evaluation.verdict_reason,
          expected_tools: turn.evaluation.expected_tools,
          actual_tools: turn.evaluation.actual_tools,
          failure_patterns: patterns,
        },
        null,
        2,
      ),
    };
  }
  return {
    steps: [
      {
        id: "x",
        label: stage.label,
        status: stage.status,
        detail: stage.detail,
      },
    ],
    log: `Stage: ${stage.label}\nStatus: ${meta.label}\n${stage.detail ?? ""}`,
  };
}

/* =========================================================================
   Turn Picker
   ========================================================================= */

function TurnPicker({
  turns,
  selected,
  onSelect,
}: {
  turns: TurnData[];
  selected: number | null;
  onSelect: (n: number) => void;
}) {
  return (
    <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm px-4 py-3">
      <div className="flex items-center gap-3 overflow-x-auto">
        <span className="text-[10px] font-bold tracking-widest text-brand-muted uppercase flex-shrink-0">
          Turns
        </span>
        {turns.map((t) => {
          const s = turnOverallStatus(t);
          const meta = STATUS_META[s];
          const active = selected === t.turn_number;
          return (
            <button
              key={t.turn_number}
              onClick={() => onSelect(t.turn_number)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition flex-shrink-0 text-sm
                ${active ? "bg-brand-cream border-brand-pink ring-2 ring-brand-pink/20" : `${meta.bg} ${meta.border} hover:border-brand-pink/50`}`}
            >
              <span
                className={`w-5 h-5 rounded-full text-[10px] font-bold flex items-center justify-center ${active ? "bg-brand-pink text-white" : "bg-white text-brand-navy border border-[#e8d8d2]"}`}
              >
                {t.turn_number}
              </span>
              <StatusDot status={s} size={8} />
              <span className="text-xs font-medium text-brand-navy">
                {fmtMs(t.latencies.total_ms)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* =========================================================================
   Transcript Panel
   ========================================================================= */

function TranscriptPanel({
  turns,
  selectedTurn,
  onSelectTurn,
}: {
  turns: TurnData[];
  selectedTurn: number | null;
  onSelectTurn: (n: number) => void;
}) {
  return (
    <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm h-full flex flex-col">
      <div className="px-4 py-3 border-b border-[#f5e9e4]">
        <h3 className="text-xs font-bold text-brand-navy uppercase tracking-widest">
          Transcript
        </h3>
      </div>
      <div className="flex-1 overflow-auto px-4 py-3 space-y-3">
        {turns.map((t) => (
          <div
            key={t.turn_number}
            onClick={() => onSelectTurn(t.turn_number)}
            className={`cursor-pointer rounded-lg p-2 -mx-2 transition ${selectedTurn === t.turn_number ? "bg-[#fff0f7]" : "hover:bg-[#fdf5f2]"}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-brand-muted uppercase">
                Turn {t.turn_number}
              </span>
              <StatusDot status={turnOverallStatus(t)} size={7} />
            </div>
            <div className="flex items-start gap-2 mb-1.5">
              <User
                size={12}
                className="text-brand-muted mt-0.5 flex-shrink-0"
              />
              <p className="text-xs text-brand-navy">
                {t.user_text || (
                  <em className="text-brand-muted">no transcript</em>
                )}
              </p>
            </div>
            <div className="flex items-start gap-2">
              <Bot size={12} className="text-brand-pink mt-0.5 flex-shrink-0" />
              <p className="text-xs text-brand-slate">
                {t.bot_text || (
                  <em className="text-brand-muted">no response</em>
                )}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* =========================================================================
   Call List (left sidebar)
   ========================================================================= */

function CallList({
  calls,
  loading,
  selected,
  onSelect,
}: {
  calls: CallSummary[];
  loading: boolean;
  selected: string | null;
  onSelect: (sid: string) => void;
}) {
  return (
    <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm h-full flex flex-col">
      <div className="px-4 py-3 border-b border-[#f5e9e4] flex items-center justify-between">
        <h3 className="text-xs font-bold text-brand-navy uppercase tracking-widest">
          Recent Calls
        </h3>
        <span className="text-xs text-brand-muted">{calls.length}</span>
      </div>
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="p-8 text-center">
            <Loader2
              size={20}
              className="animate-spin text-brand-pink mx-auto mb-2"
            />
            <p className="text-xs text-brand-muted">Loading…</p>
          </div>
        ) : calls.length === 0 ? (
          <div className="p-8 text-center text-xs text-brand-muted">
            No calls yet.
          </div>
        ) : (
          <div className="divide-y divide-[#f5e9e4]">
            {calls.map((c) => {
              const active = selected === c.call_sid;
              return (
                <button
                  key={c.call_sid}
                  onClick={() => onSelect(c.call_sid)}
                  className={`w-full text-left px-4 py-3 transition ${active ? "bg-[#fff0f7] border-l-2 border-brand-pink" : "hover:bg-[#fdf5f2]"}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-[11px] text-brand-navy bg-brand-cream px-1.5 py-0.5 rounded">
                      {c.call_sid.slice(0, 14)}…
                    </span>
                    {c.issues_count > 0 ? (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-[#fff0ee] text-brand-salmon text-[10px] font-semibold rounded">
                        <AlertTriangle size={10} />
                        {c.issues_count}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-[#f0fdf4] text-[#16a34a] text-[10px] font-semibold rounded">
                        <CheckCircle size={10} />
                        OK
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-brand-muted">
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {fmtDuration(c.duration_seconds)}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare size={10} />
                      {c.turn_count}
                    </span>
                    <span className="ml-auto font-mono">
                      {fmtMs(c.avg_latency_ms)}
                    </span>
                  </div>
                  <div className="text-[10px] text-brand-muted mt-0.5">
                    {fmtTime(c.started_at)}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* =========================================================================
   Inspector (right panel for stage detail)
   ========================================================================= */

function Inspector({
  turn,
  roadmap,
  selectedTurn,
  onSelectTurn,
}: {
  turn: TurnData | null;
  roadmap: RoadmapData | null;
  selectedTurn: number | null;
  onSelectTurn: (n: number) => void;
}) {
  if (!turn) {
    return (
      <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm p-5 text-xs text-brand-muted">
        Select a turn to see evaluation details.
      </div>
    );
  }
  const patterns = parsePatterns(turn.evaluation.failure_patterns);
  const overall = turnOverallStatus(turn);

  return (
    <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm">
      <div className="px-4 py-3 border-b border-[#f5e9e4] flex items-center justify-between">
        <h3 className="text-xs font-bold text-brand-navy uppercase tracking-widest">
          Inspector — Turn {turn.turn_number}
        </h3>
        <StatusPill status={overall} />
      </div>
      <div className="px-4 py-3 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <Kpi
            label="STT"
            value={fmtMs(turn.latencies.stt_ms)}
            tone={latencyToneClass(turn.latencies.stt_ms, 2500, 4000)}
          />
          <Kpi
            label="LLM"
            value={fmtMs(turn.latencies.llm_ms)}
            tone={latencyToneClass(turn.latencies.llm_ms, 1500, 3000)}
          />
          <Kpi
            label="TTS"
            value={fmtMs(turn.latencies.tts_ms)}
            tone={latencyToneClass(turn.latencies.tts_ms, 3000, 5000)}
          />
          <Kpi
            label="Total"
            value={fmtMs(turn.latencies.total_ms)}
            tone={latencyToneClass(turn.latencies.total_ms, 2500, 4500)}
          />
        </div>
        {patterns.length > 0 && (
          <div>
            <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-1">
              Failure Patterns
            </div>
            <div className="flex flex-wrap gap-1">
              {patterns.map((p, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#fff0ee] text-brand-salmon border border-[#ffc2b4] rounded-full text-[10px] font-semibold"
                >
                  {p[0]} {p[1]}
                </span>
              ))}
            </div>
          </div>
        )}
        {(turn.evaluation.expected_tools || turn.evaluation.actual_tools) && (
          <div>
            <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-1">
              Tools
            </div>
            <div className="text-[11px] text-brand-slate">
              <span className="font-medium text-brand-navy">Expected:</span>{" "}
              {turn.evaluation.expected_tools ?? "—"}
            </div>
            <div className="text-[11px] text-brand-slate">
              <span className="font-medium text-brand-navy">Actual:</span>{" "}
              {turn.evaluation.actual_tools ?? "—"}
            </div>
          </div>
        )}
        {turn.new_metrics && (
          <>
            <div className="border-t border-[#f5e9e4] pt-3 mt-3">
              <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">
                New Metrics
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-brand-slate">
                    TTS Situation
                  </span>
                  <span className="text-[11px] font-medium text-brand-navy">
                    {turn.new_metrics.tts_situation ?? "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-brand-slate">TTS Mood</span>
                  <span className="text-[11px] font-medium text-brand-navy">
                    {turn.new_metrics.tts_mood ?? "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-brand-slate">
                    STT Confidence
                  </span>
                  <span className="text-[11px] font-medium text-brand-navy">
                    {turn.new_metrics.stt_confidence
                      ? `${(turn.new_metrics.stt_confidence * 100).toFixed(1)}%`
                      : "—"}
                  </span>
                </div>
              </div>
            </div>
            {(turn.new_metrics.layer1_decision ||
              turn.new_metrics.layer2_raw_output ||
              turn.new_metrics.layer3_changes) && (
              <div className="border-t border-[#f5e9e4] pt-3 mt-3">
                <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">
                  Layer Observability
                </div>
                <div className="space-y-2">
                  {turn.new_metrics.layer1_decision && (
                    <div>
                      <span className="text-[11px] text-brand-slate block mb-1">
                        Layer 1 Decision
                      </span>
                      <pre className="text-[10px] bg-brand-cream p-2 rounded text-brand-navy overflow-x-auto">
                        {typeof turn.new_metrics.layer1_decision === "string"
                          ? turn.new_metrics.layer1_decision
                          : JSON.stringify(
                              turn.new_metrics.layer1_decision,
                              null,
                              2,
                            )}
                      </pre>
                    </div>
                  )}
                  {turn.new_metrics.layer2_raw_output && (
                    <div>
                      <span className="text-[11px] text-brand-slate block mb-1">
                        Layer 2 Raw Output
                      </span>
                      <pre className="text-[10px] bg-brand-cream p-2 rounded text-brand-navy overflow-x-auto whitespace-pre-wrap">
                        {turn.new_metrics.layer2_raw_output}
                      </pre>
                    </div>
                  )}
                  {turn.new_metrics.layer3_changes && (
                    <div>
                      <span className="text-[11px] text-brand-slate block mb-1">
                        Layer 3 Changes
                      </span>
                      <pre className="text-[10px] bg-brand-cream p-2 rounded text-brand-navy overflow-x-auto">
                        {typeof turn.new_metrics.layer3_changes === "string"
                          ? turn.new_metrics.layer3_changes
                          : JSON.stringify(
                              turn.new_metrics.layer3_changes,
                              null,
                              2,
                            )}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
            {turn.new_metrics.validation_breakdown &&
              Object.keys(turn.new_metrics.validation_breakdown).length > 0 && (
                <div className="border-t border-[#f5e9e4] pt-3 mt-3">
                  <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">
                    Validation Breakdown
                  </div>
                  <pre className="text-[10px] bg-brand-cream p-2 rounded text-brand-navy overflow-x-auto">
                    {typeof turn.new_metrics.validation_breakdown === "string"
                      ? turn.new_metrics.validation_breakdown
                      : JSON.stringify(
                          turn.new_metrics.validation_breakdown,
                          null,
                          2,
                        )}
                  </pre>
                </div>
              )}
          </>
        )}

        {/* Per-call all-turns report */}
        {roadmap && (
          <AllTurnsReport
            roadmap={roadmap}
            selectedTurn={selectedTurn}
            onSelect={onSelectTurn}
          />
        )}
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="bg-brand-cream rounded-lg px-3 py-2">
      <div className="text-[10px] font-medium uppercase tracking-wide text-brand-muted">
        {label}
      </div>
      <div className={`text-sm font-bold ${tone ?? "text-brand-navy"}`}>
        {value}
      </div>
    </div>
  );
}

/* =========================================================================
   Call-ID Panel — shown below Inspector; copy + download report
   ========================================================================= */

function CallIdPanel({ callSid }: { callSid: string }) {
  const [copying, setCopying] = useState<"json" | "md" | null>(null);
  const [copied, setCopied] = useState<"json" | "md" | null>(null);
  const [downloading, setDownloading] = useState<"json" | "md" | null>(null);
  const [viewing, setViewing] = useState<"json" | "md" | null>(null);
  const [sidCopied, setSidCopied] = useState(false);

  const fetchReport = async (fmt: "json" | "md") => {
    const apiFormat = fmt === "md" ? "markdown" : "json";
    const res = await fetch(`/api/dashboard/call-report/${callSid}?report_format=${apiFormat}`);
    const text = await res.text();
    if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
    return text;
  };

  const copyReport = async (fmt: "json" | "md") => {
    if (copying) return;
    setCopying(fmt);
    try {
      const text = await fetchReport(fmt);
      await navigator.clipboard.writeText(text);
      setCopied(fmt);
      setTimeout(() => setCopied(null), 2000);
    } catch { /* silent */ } finally {
      setCopying(null);
    }
  };

  const downloadReport = async (fmt: "json" | "md") => {
    if (downloading) return;
    setDownloading(fmt);
    try {
      const text = await fetchReport(fmt);
      const blob = new Blob([text], { type: fmt === "md" ? "text/markdown" : "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${callSid}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* silent */ } finally {
      setDownloading(null);
    }
  };

  const viewReport = async (fmt: "json" | "md") => {
    if (viewing) return;
    setViewing(fmt);
    try {
      const apiFormat = fmt === "md" ? "markdown" : "json";
      window.open(`/api/dashboard/call-report/${callSid}?report_format=${apiFormat}`, "_blank", "noopener,noreferrer");
    } finally {
      setViewing(null);
    }
  };

  const copySid = async () => {
    await navigator.clipboard.writeText(callSid);
    setSidCopied(true);
    setTimeout(() => setSidCopied(false), 1500);
  };

  const busy = !!copying || !!downloading || !!viewing;

  return (
    <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm">
      <div className="px-4 py-3 border-b border-[#f5e9e4]">
        <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-1.5">
          Call ID
        </div>
        <div className="flex items-center gap-2">
          <span className="flex-1 font-mono text-[11px] text-brand-navy bg-brand-cream px-2 py-1 rounded-lg border border-[#e8d8d2] truncate">
            {callSid}
          </span>
          <button
            onClick={copySid}
            className="flex items-center justify-center w-7 h-7 rounded-lg border border-[#e8d8d2] bg-brand-cream text-brand-muted hover:border-brand-pink/50 hover:text-brand-navy transition"
            title="Copy call ID"
          >
            {sidCopied ? <Check size={12} className="text-[#16a34a]" /> : <Copy size={12} />}
          </button>
        </div>
      </div>

      <div className="px-4 py-3 space-y-2">
        {/* Copy row */}
        <div>
          <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-1.5">
            Copy Report
          </div>
          <div className="flex gap-2">
            {(["md", "json"] as const).map((fmt) => (
              <button
                key={fmt}
                onClick={() => copyReport(fmt)}
                disabled={busy}
                className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg border text-[11px] font-semibold transition disabled:opacity-50
                  ${copied === fmt
                    ? "bg-[#f0fdf4] border-[#bbf7d0] text-[#16a34a]"
                    : "bg-brand-cream border-[#e8d8d2] text-brand-navy hover:border-brand-pink/50"
                  }`}
              >
                {copied === fmt
                  ? <><Check size={11} /> Copied</>
                  : copying === fmt
                  ? <><Loader2 size={11} className="animate-spin" /> …</>
                  : <><Copy size={11} /> {fmt.toUpperCase()}</>}
              </button>
            ))}
          </div>
        </div>

        {/* View row */}
        <div>
          <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-1.5">
            View Report
          </div>
          <div className="flex gap-2">
            {(["md", "json"] as const).map((fmt) => (
              <button
                key={fmt}
                onClick={() => viewReport(fmt)}
                disabled={busy}
                className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg border border-[#e8d8d2] bg-white text-brand-navy text-[11px] font-semibold hover:border-brand-pink/50 transition disabled:opacity-50"
              >
                {viewing === fmt
                  ? <><Loader2 size={11} className="animate-spin" /> …</>
                  : <><FileText size={11} /> {fmt.toUpperCase()}</>}
              </button>
            ))}
          </div>
        </div>

        {/* Download row */}
        <div>
          <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-1.5">
            Download Report
          </div>
          <div className="flex gap-2">
            {(["md", "json"] as const).map((fmt) => (
              <button
                key={fmt}
                onClick={() => downloadReport(fmt)}
                disabled={busy}
                className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg border border-[#e8d8d2] bg-brand-cream text-brand-navy text-[11px] font-semibold hover:border-brand-pink/50 transition disabled:opacity-50"
              >
                {downloading === fmt
                  ? <><Loader2 size={11} className="animate-spin" /> …</>
                  : <><Download size={11} /> {fmt.toUpperCase()}</>}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================================================================
   Copy Report Button — copies full MD or JSON to clipboard
   ========================================================================= */

function CopyReportButton({ callSid }: { callSid: string }) {
  const [copying, setCopying] = useState<"json" | "md" | null>(null);
  const [copied, setCopied] = useState<"json" | "md" | null>(null);

  const copy = async (fmt: "json" | "md") => {
    if (copying) return;
    setCopying(fmt);
    try {
      const apiFormat = fmt === "md" ? "markdown" : "json";
      const res = await fetch(
        `/api/dashboard/call-report/${callSid}?report_format=${apiFormat}`,
      );
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      setCopied(fmt);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      /* silent */
    } finally {
      setCopying(null);
    }
  };

  const btn = (fmt: "json" | "md", label: string) => {
    const active = copied === fmt;
    const loading = copying === fmt;
    return (
      <button
        key={fmt}
        onClick={() => copy(fmt)}
        disabled={!!copying}
        title={`Copy full ${fmt.toUpperCase()} report`}
        className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border transition
          ${active
            ? "bg-[#f0fdf4] border-[#bbf7d0] text-[#16a34a]"
            : "bg-brand-cream border-[#e8d8d2] text-brand-muted hover:border-brand-pink/50 hover:text-brand-navy"
          } disabled:opacity-50`}
      >
        {active ? <Check size={10} /> : loading ? <Loader2 size={10} className="animate-spin" /> : <Copy size={10} />}
        {active ? "Copied" : label}
      </button>
    );
  };

  return (
    <div className="flex items-center gap-1">
      {btn("md", "MD")}
      {btn("json", "JSON")}
    </div>
  );
}

/* =========================================================================
   All-Turns Report — compact per-turn row list
   ========================================================================= */

function AllTurnsReport({
  roadmap,
  selectedTurn,
  onSelect,
}: {
  roadmap: RoadmapData;
  selectedTurn: number | null;
  onSelect: (n: number) => void;
}) {
  if (!roadmap.turns.length) return null;
  return (
    <div className="border-t border-[#f5e9e4] pt-3 mt-1">
      <div className="text-[10px] font-bold text-brand-muted uppercase tracking-widest mb-2">
        All Turns — {roadmap.turns.length} total
      </div>
      <div className="space-y-1 max-h-[240px] overflow-y-auto pr-1">
        {roadmap.turns.map((t) => {
          const s = turnOverallStatus(t);
          const meta = STATUS_META[s];
          const active = selectedTurn === t.turn_number;
          return (
            <button
              key={t.turn_number}
              onClick={() => onSelect(t.turn_number)}
              className={`w-full text-left px-2 py-1.5 rounded-lg border transition ${
                active
                  ? "bg-[#fff0f7] border-brand-pink/30"
                  : "bg-white border-[#f5e9e4] hover:border-brand-pink/30 hover:bg-[#fdf5f2]"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-5 h-5 rounded-full text-[10px] font-bold flex items-center justify-center shrink-0 ${
                    active ? "bg-brand-pink text-white" : `${meta.bg} ${meta.text} border ${meta.border}`
                  }`}
                >
                  {t.turn_number}
                </span>
                <StatusDot status={s} size={7} />
                <div className="flex-1 grid grid-cols-3 gap-0.5 text-xs font-mono">
                  <span className={latencyToneClass(t.latencies.stt_ms, 2500, 4000)}>
                    S {fmtMs(t.latencies.stt_ms)}
                  </span>
                  <span className={latencyToneClass(t.latencies.llm_ms, 1500, 3000)}>
                    L {fmtMs(t.latencies.llm_ms)}
                  </span>
                  <span className={`font-semibold ${latencyToneClass(t.latencies.total_ms, 2500, 4500)}`}>
                    {fmtMs(t.latencies.total_ms)}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** Single call recording URL: prefer combined stereo (caller_audio_url), else agent-only. */
function resolveCallAudioUrl(roadmap: RoadmapData): string | null {
  const c = roadmap.caller_audio_url?.trim();   // combined stereo call recording
  const a = roadmap.agent_audio_url?.trim();    // agent-only fallback
  if (c) return c;
  if (a) return a;
  return null;
}

function toPlayableAudioUrl(url: string): string {
  return url.replace(
    "gs://sailly-recordings-eu/",
    "https://storage.googleapis.com/sailly-recordings-eu/",
  );
}

function fmtAudioClock(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5, 1.75, 2] as const;

function CallAudioBar({ src }: { src: string | null }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(0);
  const [rate, setRate] = useState(1);

  useEffect(() => {
    setCurrent(0);
    setDuration(0);
    setPlaying(false);
  }, [src]);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setCurrent(el.currentTime);
    const onDur = () => {
      if (Number.isFinite(el.duration)) setDuration(el.duration);
    };
    const onEnd = () => setPlaying(false);
    const onPause = () => setPlaying(false);
    const onPlay = () => setPlaying(true);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onDur);
    el.addEventListener("ended", onEnd);
    el.addEventListener("pause", onPause);
    el.addEventListener("play", onPlay);
    return () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onDur);
      el.removeEventListener("ended", onEnd);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("play", onPlay);
    };
  }, [src]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  }, [rate]);

  const toggle = () => {
    const el = audioRef.current;
    if (!el || !src) return;
    if (playing) {
      el.pause();
    } else {
      void el.play().catch(() => setPlaying(false));
    }
  };

  const onSeek = (v: number) => {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = v;
    setCurrent(v);
  };

  if (!src) {
    return (
      <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm px-4 py-3">
        <div className="flex items-center gap-2.5 text-brand-navy">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#fdf5f2] text-brand-pink">
            <Headphones size={16} aria-hidden />
          </span>
          <div>
            <p className="text-xs font-semibold text-brand-navy">Call audio</p>
            <p className="text-[11px] text-brand-muted">
              No recording for this call.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const href = toPlayableAudioUrl(src);
  const max = duration > 0 ? duration : 1;

  return (
    <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm px-4 py-3">
      <div className="mb-2.5 flex items-center gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#fdf5f2] text-brand-pink">
          <Headphones size={16} aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-brand-navy">Call audio</p>
          <p className="text-[10px] text-brand-muted">Full call — one track</p>
        </div>
      </div>

      <audio ref={audioRef} src={href} preload="metadata" className="hidden" />

      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:gap-3">
        <button
          type="button"
          onClick={toggle}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#e8d8d2] bg-brand-cream text-brand-navy transition hover:border-brand-pink/50"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <Pause size={16} fill="currentColor" />
          ) : (
            <Play size={16} fill="currentColor" className="pl-0.5" />
          )}
        </button>

        <div className="min-w-0 flex-1">
          <input
            type="range"
            min={0}
            max={max}
            step={0.1}
            value={Math.min(current, max)}
            onChange={(e) => onSeek(Number(e.target.value))}
            className="h-1.5 w-full cursor-pointer accent-brand-pink"
            aria-label="Seek"
          />
          <div className="mt-0.5 flex justify-between text-[10px] font-mono text-brand-muted">
            <span>{fmtAudioClock(current)}</span>
            <span>{fmtAudioClock(duration)}</span>
          </div>
        </div>

        <label className="flex shrink-0 items-center gap-1.5 text-[11px] text-brand-slate">
          <span className="whitespace-nowrap text-brand-muted">Speed</span>
          <select
            value={rate}
            onChange={(e) => setRate(Number(e.target.value))}
            className="rounded-md border border-[#e8d8d2] bg-white px-2 py-1 text-xs font-medium text-brand-navy"
          >
            {PLAYBACK_RATES.map((r) => (
              <option key={r} value={r}>
                {r}×
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}

/* =========================================================================
   Main Page
   ========================================================================= */

export default function CallAnalysisPage() {
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [callsLoading, setCallsLoading] = useState(true);
  const [callsError, setCallsError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const [selectedCall, setSelectedCall] = useState<string | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);

  const [selectedTurn, setSelectedTurn] = useState<number | null>(null);
  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const [selectedSub, setSelectedSub] = useState<string | null>(null);

  const loadCalls = useCallback(async () => {
    try {
      setCallsError(null);
      const res = await fetch("/api/dashboard/call-analysis?limit=100");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCalls(data.calls ?? []);
    } catch {
      setCallsError(
        "Failed to load calls. The analysis service may be starting up.",
      );
    } finally {
      setCallsLoading(false);
    }
  }, []);

  const loadRoadmap = useCallback(async (callSid: string) => {
    setRoadmapLoading(true);
    setRoadmapError(null);
    setRoadmap(null);
    setSelectedStage(null);
    setSelectedSub(null);
    try {
      const res = await fetch(
        `/api/dashboard/call-analysis/${callSid}/roadmap`,
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: RoadmapData = await res.json();
      setRoadmap(data);
      if (data.turns && data.turns.length > 0) {
        const firstFailing = data.turns.find(
          (t) => turnOverallStatus(t) === "fail",
        );
        setSelectedTurn((firstFailing ?? data.turns[0]).turn_number);
      } else {
        setSelectedTurn(null);
      }
    } catch (e: any) {
      setRoadmapError(e?.message ?? "Failed to load roadmap");
    } finally {
      setRoadmapLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCalls();
  }, [loadCalls]);
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(loadCalls, 15000);
    return () => clearInterval(id);
  }, [autoRefresh, loadCalls]);

  useEffect(() => {
    if (selectedCall) loadRoadmap(selectedCall);
  }, [selectedCall, loadRoadmap]);

  const turn = useMemo<TurnData | null>(() => {
    if (!roadmap || selectedTurn === null) return null;
    return roadmap.turns.find((t) => t.turn_number === selectedTurn) ?? null;
  }, [roadmap, selectedTurn]);

  const activeStage: Stage | null = useMemo(() => {
    if (!turn || !selectedStage) return null;
    return turn.stages.find((s) => s.id === selectedStage) ?? null;
  }, [turn, selectedStage]);

  // Auto-open first failing stage when turn changes
  useEffect(() => {
    if (!turn) {
      setSelectedStage(null);
      return;
    }
    const firstFail = turn.stages.find((s) => s.status === "fail");
    const firstDegraded = turn.stages.find((s) => s.status === "degraded");
    setSelectedStage(
      (firstFail ?? firstDegraded ?? turn.stages[0])?.id ?? null,
    );
    setSelectedSub(null);
  }, [turn]);

  return (
    <div className="min-h-screen bg-transparent p-4 md:p-6">
      <div className="max-w-[1800px] mx-auto space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-brand-navy flex items-center gap-3">
              <Activity size={26} className="text-brand-pink" />
              Call Analysis
            </h1>
            <p className="text-sm text-brand-slate mt-1">
              Per-turn pipeline trace · 12 stages · expected vs. actual
              trajectory
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-brand-slate cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto-refresh
            </label>
            <button
              onClick={loadCalls}
              className="flex items-center gap-2 px-3 py-1.5 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy transition text-sm"
            >
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>
        </div>

        {callsError && (
          <div className="bg-[#fff0ee] border border-[#ffc2b4] rounded-lg p-3 flex items-center gap-2 text-sm text-brand-salmon">
            <AlertTriangle size={16} />
            {callsError}
          </div>
        )}

        {/* 3-column layout: calls | pipeline | transcript */}
        <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)_320px] gap-4 h-[calc(100vh-180px)]">
          {/* Left: call list */}
          <div className="min-h-0">
            <CallList
              calls={calls}
              loading={callsLoading}
              selected={selectedCall}
              onSelect={setSelectedCall}
            />
          </div>

          {/* Middle: pipeline */}
          <div className="min-h-0 flex flex-col gap-4 overflow-auto pr-1">
            {!selectedCall && (
              <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm p-8 text-center">
                <Activity size={28} className="text-brand-muted mx-auto mb-3" />
                <p className="text-sm text-brand-slate">
                  Select a call on the left to inspect its pipeline.
                </p>
              </div>
            )}
            {selectedCall && roadmapLoading && (
              <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm p-8 text-center">
                <Loader2
                  size={20}
                  className="animate-spin text-brand-pink mx-auto mb-2"
                />
                <p className="text-sm text-brand-slate">
                  Loading pipeline trace…
                </p>
              </div>
            )}
            {roadmapError && (
              <div className="bg-[#fff0ee] border border-[#ffc2b4] rounded-lg p-3 text-sm text-brand-salmon">
                {roadmapError}
              </div>
            )}
            {roadmap && (
              <>
                {/* Call header bar */}
                <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm px-4 py-3 flex items-center gap-4 flex-wrap">
                  <span className="font-mono text-xs text-brand-navy bg-brand-cream px-2 py-0.5 rounded">
                    {roadmap.call_sid}
                  </span>
                  <span className="flex items-center gap-1.5 text-xs text-brand-slate">
                    <Clock size={12} />
                    {fmtDuration(roadmap.duration_seconds)}
                  </span>
                  <span className="flex items-center gap-1.5 text-xs text-brand-slate">
                    <MessageSquare size={12} />
                    {roadmap.turns.length} turns
                  </span>
                  {roadmap.outcome && (
                    <span className="text-xs text-brand-slate">
                      <span className="text-brand-muted">Outcome:</span>{" "}
                      <span className="font-semibold text-brand-navy">
                        {roadmap.outcome}
                      </span>
                    </span>
                  )}
                  {roadmap.quality_score !== null && (
                    <span className="text-xs text-brand-slate">
                      <span className="text-brand-muted">Quality:</span>{" "}
                      <span className="font-semibold text-brand-navy">
                        {roadmap.quality_score?.toFixed(2)}
                      </span>
                    </span>
                  )}
                </div>

                {/* Transcript Panel — moved right after call header */}
                {turn && (
                  <div className="min-h-[200px]">
                    <TranscriptPanel
                      turns={roadmap.turns}
                      selectedTurn={selectedTurn}
                      onSelectTurn={setSelectedTurn}
                    />
                  </div>
                )}

                {/* Layer 1: 12-stage pipeline */}
                {turn && (
                  <div className="bg-white border border-[#e8d8d2] rounded-xl shadow-sm">
                    <div className="px-4 py-3 border-b border-[#f5e9e4] flex items-center justify-between">
                      <h3 className="text-xs font-bold text-brand-navy uppercase tracking-widest">
                        Pipeline · 12 Stages
                      </h3>
                      <div className="flex items-center gap-2 text-[11px]">
                        <StatusPill status="ok" />
                        <StatusPill status="degraded" />
                        <StatusPill status="fail" />
                      </div>
                    </div>
                    <div className="px-4 py-4 overflow-x-auto">
                      <div className="flex items-stretch gap-0">
                        {turn.stages.map((stage, i) => (
                          <React.Fragment key={stage.id}>
                            <StageCard
                              stage={stage}
                              index={i}
                              selected={selectedStage === stage.id}
                              onClick={() => {
                                setSelectedStage(stage.id);
                                setSelectedSub(null);
                              }}
                            />
                            {i < turn.stages.length - 1 && (
                              <StageConnector status={stage.status} />
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Layer 2 + Layer 3: stage detail */}
                {turn && activeStage && (
                  <Layer2Panel
                    stage={activeStage}
                    turn={turn}
                    selectedSub={selectedSub}
                    onSelectSub={setSelectedSub}
                  />
                )}

                {/* Call audio: one track, same slot as before (after stage detail, before transcript) */}
                <CallAudioBar
                  key={roadmap.call_sid}
                  src={resolveCallAudioUrl(roadmap)}
                />
              </>
            )}
          </div>

          {/* Right: inspector + call-id panel */}
          <div className="min-h-0 flex flex-col gap-4 overflow-auto pr-1">
            <Inspector
              turn={turn}
              roadmap={roadmap}
              selectedTurn={selectedTurn}
              onSelectTurn={(n) => {
                setSelectedTurn(n);
                setSelectedStage(null);
                setSelectedSub(null);
              }}
            />
            {roadmap && <CallIdPanel callSid={roadmap.call_sid} />}
          </div>
        </div>
      </div>
    </div>
  );
}

/* eslint-disable @typescript-eslint/no-unused-vars */
void Waves;

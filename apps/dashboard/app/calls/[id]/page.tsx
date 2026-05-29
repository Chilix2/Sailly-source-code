'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Clock,
  Euro,
  Star,
  SmilePlus,
  Target,
  Globe,
  ShieldAlert,
  ShieldCheck,
  MessageSquare,
  Zap,
  BarChart3,
  DollarSign,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface TranscriptTurn {
  role: string;
  content: string;
  turn_number: number;
  created_at: string;
}

interface ToolCall {
  tool_name: string;
  input_data: string;
  result: string;
  created_at: string;
}

interface QualityEvaluation {
  score: number;
  issues: string[] | string;
  tool_usage_score: number;
  greeting_score: number;
  resolution_score: number;
}

interface AnalyticsData {
  cost?: Record<string, unknown>;
  quality?: { score: number; issues: string[] };
  summary?: { text: string; intent: string; caller_name: string; tool_sequence: string[] };
  sentiment?: { overall: string; positive_signals: string[]; negative_signals: string[] };
  metrics?: Record<string, unknown>;
}

interface CallData {
  id: number;
  call_sid: string;
  caller_number: string;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  quality_score: number;
  outcome: string;
  sentiment: string;
  language: string;
  was_escalated: boolean;
  total_cost: number;
  total_cost_tokens: number;
  total_cost_telephony: number;
  recording_consent_at: string | null;
  analytics_data: AnalyticsData | null;
  transcript: TranscriptTurn[];
  tool_calls: ToolCall[];
  quality_evaluation: QualityEvaluation | null;
}

type TabKey = 'transcript' | 'tools' | 'quality' | 'cost';

const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'transcript', label: 'Transcript', icon: <MessageSquare size={16} /> },
  { key: 'tools', label: 'Tool Calls', icon: <Zap size={16} /> },
  { key: 'quality', label: 'Quality', icon: <BarChart3 size={16} /> },
  { key: 'cost', label: 'Cost Breakdown', icon: <DollarSign size={16} /> },
];

function outcomeBadge(outcome: string) {
  const map: Record<string, string> = {
    order: 'bg-[#f0fdf4] text-[#16a34a]',
    reservation: 'bg-blue-950/50 text-brand-slate',
    inquiry: 'bg-[#fff8ea] text-brand-peach',
    hangup: 'bg-[#fff0ee] text-brand-salmon',
  };
  return map[outcome] ?? 'bg-brand-cream text-brand-slate';
}

function qualityColor(score: number) {
  if (score >= 8) return 'bg-[#f0fdf4] text-[#16a34a]';
  if (score >= 6) return 'bg-[#fff8ea] text-brand-peach';
  return 'bg-[#fff0ee] text-brand-salmon';
}

function qualityBarColor(score: number) {
  if (score >= 8) return 'bg-green-500';
  if (score >= 6) return 'bg-yellow-500';
  return 'bg-red-500';
}

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('de-DE', { timeStyle: 'medium' });
}

function tryParseJSON(str: string): unknown {
  try {
    return JSON.parse(str);
  } catch {
    return str;
  }
}

function QualityBar({ label, score, max = 10 }: { label: string; score: number; max?: number }) {
  const pct = (score / max) * 100;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center text-xs">
        <span className="text-brand-slate">{label}</span>
        <span className="text-brand-navy font-mono">{score}/{max}</span>
      </div>
      <div className="w-full h-2 bg-brand-cream rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${qualityBarColor(score)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const callId = params.id as string;

  const [call, setCall] = useState<CallData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('transcript');

  useEffect(() => {
    if (!callId) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        const res = await fetch(`/api/dashboard/calls/${callId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setCall(json.data ?? json);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [callId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <div className="flex items-center gap-3 text-brand-slate">
          <RefreshCw size={20} className="animate-spin" />
          <span>Loading call details…</span>
        </div>
      </div>
    );
  }

  if (error || !call) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <div className="bg-[#fff0ee] border border-[#ffd8d0] rounded-lg p-6 max-w-md text-center space-y-3">
          <AlertCircle size={32} className="text-brand-salmon mx-auto" />
          <p className="text-brand-salmon font-semibold">Failed to load call</p>
          <p className="text-brand-salmon text-sm">{error}</p>
          <button
            onClick={() => router.push('/calls')}
            className="px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] text-brand-navy rounded-lg text-sm transition"
          >
            Back to Calls
          </button>
        </div>
      </div>
    );
  }

  const totalCost = call.total_cost ?? (call.total_cost_tokens + call.total_cost_telephony);

  const costChartData = [
    { name: 'Gemini', value: call.total_cost_tokens, fill: '#a855f7' },
    { name: 'Twilio', value: call.total_cost_telephony, fill: '#3b82f6' },
    { name: 'Total', value: totalCost, fill: 'hsl(192, 100%, 50%)' },
  ];

  const transcript = call.transcript ?? [];
  const toolCalls = call.tool_calls ?? [];
  const qe = call.quality_evaluation;
  const analytics = call.analytics_data;

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Back button */}
        <button
          onClick={() => router.push('/calls')}
          className="flex items-center gap-2 text-brand-slate hover:text-white text-sm transition"
        >
          <ArrowLeft size={16} />
          Back to Call History
        </button>

        {/* Header */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-xl font-bold text-brand-navy font-mono break-all">{call.call_sid}</h1>
                <span className={`px-2 py-1 rounded text-xs font-medium ${outcomeBadge(call.outcome)}`}>
                  {call.outcome}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${qualityColor(call.quality_score)}`}>
                  {call.quality_score.toFixed(1)}/10
                </span>
              </div>
              <p className="text-brand-slate text-sm">
                {formatDateTime(call.started_at)}
                {call.ended_at && <>{' — '}{formatTime(call.ended_at)}</>}
                {' · '}
                {formatDuration(call.duration_seconds)}
                {' · '}
                Caller: {call.caller_number}
              </p>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard icon={<Clock size={18} className="text-brand-muted" />} label="Duration" value={formatDuration(call.duration_seconds)} />
          <SummaryCard icon={<Euro size={18} className="text-brand-muted" />} label="Total Cost" value={`€${totalCost.toFixed(3)}`} />
          <SummaryCard icon={<Star size={18} className="text-brand-muted" />} label="Quality" value={`${call.quality_score.toFixed(1)}/10`} />
          <SummaryCard icon={<SmilePlus size={18} className="text-brand-muted" />} label="Sentiment" value={call.sentiment ?? '—'} />
          <SummaryCard icon={<Target size={18} className="text-brand-muted" />} label="Outcome" value={call.outcome} />
          <SummaryCard icon={<Globe size={18} className="text-brand-muted" />} label="Language" value={call.language?.toUpperCase() ?? '—'} />
          <SummaryCard
            icon={<ShieldAlert size={18} className="text-brand-muted" />}
            label="Escalated"
            value={call.was_escalated ? 'Yes' : 'No'}
            highlight={call.was_escalated ? 'text-brand-salmon' : 'text-[#16a34a]'}
          />
          <SummaryCard
            icon={<ShieldCheck size={18} className="text-brand-muted" />}
            label="Consent"
            value={call.recording_consent_at ? formatTime(call.recording_consent_at) : 'None'}
          />
        </div>

        {/* Analytics Summary */}
        {analytics?.summary?.text && (
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <p className="text-xs text-brand-muted uppercase tracking-wide mb-2">AI Summary</p>
            <p className="text-sm text-brand-navy leading-relaxed">{analytics.summary.text}</p>
            {analytics.summary.caller_name && (
              <p className="text-xs text-brand-muted mt-2">Caller: {analytics.summary.caller_name} · Intent: {analytics.summary.intent}</p>
            )}
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-brand-cream">
          <div className="flex gap-1 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${
                  activeTab === tab.key
                    ? 'border-accent text-brand-navy'
                    : 'border-transparent text-brand-muted hover:text-zinc-300'
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.key === 'tools' && toolCalls.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 bg-brand-cream rounded text-xs text-brand-slate">{toolCalls.length}</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg">
          {activeTab === 'transcript' && <TranscriptTab transcript={transcript} />}
          {activeTab === 'tools' && <ToolCallsTab toolCalls={toolCalls} />}
          {activeTab === 'quality' && <QualityTab evaluation={qe} analytics={analytics} />}
          {activeTab === 'cost' && <CostTab data={costChartData} tokens={call.total_cost_tokens} telephony={call.total_cost_telephony} total={totalCost} analytics={analytics} duration={call.duration_seconds} toolCount={toolCalls.length} turnCount={transcript.length} />}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: string;
}) {
  return (
    <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-brand-muted uppercase tracking-wide">{label}</p>
          <p className={`text-lg font-semibold mt-1 ${highlight ?? 'text-brand-navy'}`}>{value}</p>
        </div>
        {icon}
      </div>
    </div>
  );
}

function TranscriptTab({ transcript }: { transcript: TranscriptTurn[] }) {
  if (transcript.length === 0) {
    return <div className="p-8 text-center text-brand-muted">No transcript available</div>;
  }

  return (
    <div className="p-4 md:p-6 space-y-4 max-h-[600px] overflow-y-auto">
      {transcript.map((turn, idx) => {
        const isUser = turn.role === 'user';
        return (
          <div key={idx} className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}>
            <div
              className={`max-w-[80%] rounded-lg p-3 space-y-1 ${
                isUser
                  ? 'bg-brand-cream border border-[#e8d8d2]'
                  : 'bg-accent/10 border border-brand-pink/20'
              }`}
            >
              <div className="flex items-center gap-2 text-xs">
                <span className={isUser ? 'text-yellow-400 font-medium' : 'text-brand-pink font-medium'}>
                  {isUser ? 'Caller' : 'Agent'}
                </span>
                <span className="text-brand-muted">#{turn.turn_number}</span>
                {turn.created_at && (
                  <span className="text-brand-muted">{formatTime(turn.created_at)}</span>
                )}
              </div>
              <p className="text-sm text-brand-navy leading-relaxed">{turn.content}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ToolCallsTab({ toolCalls }: { toolCalls: ToolCall[] }) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  if (toolCalls.length === 0) {
    return <div className="p-8 text-center text-brand-muted">No tool calls recorded</div>;
  }

  return (
    <div className="p-4 md:p-6">
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-brand-cream" />
        <div className="space-y-6">
          {toolCalls.map((tc, idx) => {
            const inputParsed = tryParseJSON(tc.input_data);
            const isOpen = expanded[idx] ?? false;

            return (
              <div key={idx} className="relative pl-10">
                <div className="absolute left-2.5 top-2 w-3 h-3 rounded-full bg-brand-pink border-2 border-zinc-900" />
                <div className="bg-brand-cream rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-mono text-sm text-brand-pink font-semibold">{tc.tool_name}</span>
                    {tc.created_at && (
                      <span className="text-xs text-brand-muted">{formatTime(tc.created_at)}</span>
                    )}
                  </div>
                  <div>
                    <button
                      onClick={() => setExpanded((prev) => ({ ...prev, [idx]: !isOpen }))}
                      className="text-xs text-brand-slate hover:text-brand-pink transition"
                    >
                      {isOpen ? 'Hide details' : 'Show details'}
                    </button>
                  </div>
                  {isOpen && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <p className="text-brand-muted mb-1">Arguments</p>
                        <pre className="bg-white shadow-sm p-3 rounded overflow-x-auto text-brand-navy max-h-48 overflow-y-auto">
                          {typeof inputParsed === 'string' ? inputParsed : JSON.stringify(inputParsed, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <p className="text-brand-muted mb-1">Result</p>
                        <pre className="bg-white shadow-sm p-3 rounded overflow-x-auto text-brand-navy max-h-48 overflow-y-auto">
                          {tc.result ? (typeof tc.result === 'string' ? tc.result.slice(0, 500) : JSON.stringify(tc.result, null, 2)) : '—'}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function parseIssues(raw: string[] | string | undefined | null): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [raw];
    } catch {
      return raw.length > 0 ? [raw] : [];
    }
  }
  return [];
}

function QualityTab({ evaluation, analytics }: { evaluation: QualityEvaluation | null; analytics: AnalyticsData | null }) {
  const score = evaluation?.score ?? analytics?.quality?.score ?? null;
  const usingAnalyticsFallback = !evaluation && analytics?.quality?.score != null;

  const issues = evaluation
    ? parseIssues(evaluation.issues)
    : parseIssues(analytics?.quality?.issues);

  if (score === null) {
    return <div className="p-8 text-center text-brand-muted">No quality evaluation available</div>;
  }

  const displayScore = score <= 10 ? score : score / 10;

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center gap-6">
        <div className="w-24 h-24 rounded-full border-4 border-brand-cream flex items-center justify-center">
          <span className={`text-3xl font-bold ${displayScore >= 8 ? 'text-[#16a34a]' : displayScore >= 6 ? 'text-yellow-400' : 'text-brand-salmon'}`}>
            {displayScore.toFixed(1)}
          </span>
        </div>
        <div>
          <p className="text-brand-navy font-semibold text-lg">Quality Score</p>
          <p className="text-brand-slate text-sm">out of 10.0</p>
          {usingAnalyticsFallback && (
            <p className="text-xs text-brand-muted mt-1 italic">Source: live analytics</p>
          )}
        </div>
      </div>

      {evaluation && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QualityBar label="Greeting" score={evaluation.greeting_score} />
          <QualityBar label="Resolution" score={evaluation.resolution_score} />
          <QualityBar label="Tool Usage" score={evaluation.tool_usage_score} />
        </div>
      )}

      {analytics?.sentiment && (
        <div className="space-y-3">
          <p className="text-sm text-brand-slate font-medium">Sentiment Analysis</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {analytics.sentiment.positive_signals?.length > 0 && (
              <div className="bg-green-950/20 border border-green-900/30 rounded-lg p-4">
                <p className="text-xs text-[#16a34a] font-medium mb-2">Positive Signals</p>
                <ul className="space-y-1">
                  {analytics.sentiment.positive_signals.map((s, i) => (
                    <li key={i} className="text-sm text-[#16a34a] flex gap-2"><span>+</span><span>{s}</span></li>
                  ))}
                </ul>
              </div>
            )}
            {analytics.sentiment.negative_signals?.length > 0 && (
              <div className="bg-red-950/20 border border-red-900/30 rounded-lg p-4">
                <p className="text-xs text-brand-salmon font-medium mb-2">Negative Signals</p>
                <ul className="space-y-1">
                  {analytics.sentiment.negative_signals.map((s, i) => (
                    <li key={i} className="text-sm text-brand-salmon flex gap-2"><span>-</span><span>{s}</span></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {issues.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-brand-slate font-medium">Issues Detected</p>
          <ul className="space-y-2">
            {issues.map((issue, idx) => (
              <li key={idx} className="flex gap-2 text-sm">
                <AlertCircle size={16} className="text-brand-salmon shrink-0 mt-0.5" />
                <span className="text-brand-salmon">{issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function fmt(val: number): string {
  if (val === 0) return '€0.00000';
  // Show enough decimals to reveal non-zero digits (up to 5 after decimal)
  const fixed5 = val.toFixed(5);
  return `€${fixed5}`;
}

function CostTab({
  data,
  tokens,
  telephony,
  total,
  analytics,
  duration,
  toolCount,
  turnCount,
}: {
  data: { name: string; value: number; fill: string }[];
  tokens: number;
  telephony: number;
  total: number;
  analytics?: AnalyticsData | null;
  duration?: number;
  toolCount?: number;
  turnCount?: number;
}) {
  const tooltipStyle = {
    backgroundColor: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: '6px',
  };

  const pctTokens = total > 0 ? ((tokens / total) * 100).toFixed(1) : '—';
  const pctTelephony = total > 0 ? ((telephony / total) * 100).toFixed(1) : '—';
  const isDemoCall = total === 0;

  return (
    <div className="p-4 md:p-6 space-y-6">
      {isDemoCall && (
        <div className="bg-blue-950/20 border border-blue-900/30 rounded-lg p-4 text-sm text-brand-slate">
          <p className="font-medium text-brand-navy mb-1">Demo / Internal Test Call</p>
          <p className="text-xs">No external API billing for this session. Costs below reflect real Gemini token usage when non-zero.</p>
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-center justify-between py-3 border-b border-brand-cream">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-purple-500" />
            <span className="text-sm text-brand-navy">Gemini (Tokens)</span>
          </div>
          <div className="text-right">
            <span className="text-sm text-brand-navy font-mono">{fmt(tokens)}</span>
            <span className="text-xs text-brand-muted ml-2">{pctTokens}{total > 0 ? '%' : ''}</span>
          </div>
        </div>
        <div className="flex items-center justify-between py-3 border-b border-brand-cream">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-sm text-brand-navy">Twilio (Telephony)</span>
          </div>
          <div className="text-right">
            <span className="text-sm text-brand-navy font-mono">{fmt(telephony)}</span>
            <span className="text-xs text-brand-muted ml-2">{pctTelephony}{total > 0 ? '%' : ''}</span>
          </div>
        </div>
        <div className="flex items-center justify-between py-3">
          <span className="text-sm text-brand-navy font-semibold">Total</span>
          <span className="text-lg text-brand-pink font-bold font-mono">{fmt(total)}</span>
        </div>
      </div>

      {isDemoCall && (duration != null || toolCount != null || analytics?.summary) && (
        <div className="space-y-2">
          <p className="text-xs text-brand-muted uppercase tracking-wide">Session Metrics</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {duration != null && (
              <div className="bg-brand-cream rounded-lg p-3 text-center">
                <p className="text-xs text-brand-muted">Duration</p>
                <p className="text-brand-navy font-semibold">{formatDuration(duration)}</p>
              </div>
            )}
            {turnCount != null && (
              <div className="bg-brand-cream rounded-lg p-3 text-center">
                <p className="text-xs text-brand-muted">Turns</p>
                <p className="text-brand-navy font-semibold">{turnCount}</p>
              </div>
            )}
            {toolCount != null && (
              <div className="bg-brand-cream rounded-lg p-3 text-center">
                <p className="text-xs text-brand-muted">Tool Calls</p>
                <p className="text-brand-navy font-semibold">{toolCount}</p>
              </div>
            )}
            {analytics?.summary?.intent && (
              <div className="bg-brand-cream rounded-lg p-3 text-center col-span-2 md:col-span-1">
                <p className="text-xs text-brand-muted">Intent</p>
                <p className="text-brand-navy font-semibold capitalize">{analytics.summary.intent}</p>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <p className="text-xs text-brand-muted uppercase tracking-wide">Cost Distribution</p>
        <div className="w-full h-6 bg-brand-cream rounded-full overflow-hidden flex">
          {total > 0 ? (
            <>
              <div
                className="h-full bg-purple-500 transition-all"
                style={{ width: `${(tokens / total) * 100}%` }}
                title={`Gemini: ${fmt(tokens)}`}
              />
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: `${(telephony / total) * 100}%` }}
                title={`Twilio: ${fmt(telephony)}`}
              />
            </>
          ) : (
            <div className="h-full w-full bg-zinc-700/30 flex items-center justify-center">
              <span className="text-xs text-brand-muted">No billable cost</span>
            </div>
          )}
        </div>
        <div className="flex gap-4 text-xs text-brand-muted">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500 inline-block" /> Gemini</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> Twilio</span>
        </div>
      </div>

      {total > 0 && (
        <div>
          <p className="text-xs text-brand-muted uppercase tracking-wide mb-4">Comparison</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" horizontal={false} />
              <XAxis type="number" stroke="#71717a" tick={{ fontSize: 12 }} tickFormatter={(v) => `€${v.toFixed(5)}`} />
              <YAxis type="category" dataKey="name" stroke="#71717a" tick={{ fontSize: 12 }} width={60} />
              <Tooltip
                contentStyle={tooltipStyle}
                labelStyle={{ color: '#fafafa' }}
                formatter={(value: number) => [fmt(value), 'Cost']}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {data.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

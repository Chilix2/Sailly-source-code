'use client';

import { useState, useEffect } from 'react';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  Phone,
  Cpu,
  Wrench,
  MessageSquare,
  PhoneOff,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Activity,
  Zap,
} from 'lucide-react';

interface MonitorSnapshot {
  total_calls: number;
  fulfilled_calls: number;
  task_success_rate: number;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  active_calls: number;
  tool_call_distribution: Record<string, number>;
  end_reason_distribution: Record<string, number>;
  intent_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  data_source: string;
  window_secs: number;
}

interface MonitorBundle {
  ok: boolean;
  health_hints: string[];
  snapshot: MonitorSnapshot;
}

const PIPELINE_STAGES = [
  { id: 'inbound',  label: 'Twilio Inbound', icon: Phone,          color: 'text-blue-400' },
  { id: 'llm',      label: 'Gemini LLM',     icon: Cpu,            color: 'text-purple-400' },
  { id: 'tools',    label: 'Tool Execution', icon: Wrench,         color: 'text-yellow-400' },
  { id: 'response', label: 'Response',       icon: MessageSquare,  color: 'text-[#16a34a]' },
  { id: 'end',      label: 'Call End',       icon: PhoneOff,       color: 'text-brand-slate' },
];

function Stat({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
      <p className="text-xs text-brand-slate uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color ?? 'text-brand-navy'}`}>{value}</p>
      {sub && <p className="text-xs text-brand-muted mt-1">{sub}</p>}
    </div>
  );
}

export default function PipelinePage() {
  const [bundle, setBundle] = useState<MonitorBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/dashboard/monitor?window=3600').then(r => r.json());
      if (res?.snapshot) {
        setBundle(res as MonitorBundle);
      } else {
        setError('Monitor endpoint returned unexpected shape');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const iv = setInterval(loadData, 30000);
    return () => clearInterval(iv);
  }, []);

  const sn = bundle?.snapshot;

  function p95Color(ms: number | null) {
    if (ms == null) return 'text-brand-navy';
    if (ms < 1500) return 'text-[#16a34a]';
    if (ms < 3000) return 'text-brand-peach';
    return 'text-brand-salmon';
  }

  function successColor(rate: number | undefined) {
    if (rate == null) return 'text-brand-navy';
    if (rate >= 80) return 'text-[#16a34a]';
    if (rate >= 60) return 'text-brand-peach';
    return 'text-brand-salmon';
  }

  function topEntries(dist: Record<string, number> | undefined, n = 6) {
    if (!dist) return [];
    return Object.entries(dist).sort((a, b) => b[1] - a[1]).slice(0, n);
  }

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-brand-navy mb-2">Call Pipeline</h1>
            <p className="text-brand-slate flex items-center gap-2 text-sm">
              {bundle ? (
                <>
                  <Wifi size={14} className="text-[#16a34a]" />
                  Live — {sn?.data_source ?? ''}
                  {sn?.window_secs ? ` · ${sn.window_secs / 60}min window` : ''}
                </>
              ) : (
                <>
                  <WifiOff size={14} className="text-yellow-500" />
                  Connecting to monitor endpoint…
                </>
              )}
            </p>
          </div>
          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy text-sm transition"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Health banner */}
        {bundle && (
          <div className={`rounded-lg border p-4 flex items-center gap-3 ${
            bundle.ok ? 'bg-[#f0fdf4] border-green-200' : 'bg-[#fff8ea] border-yellow-200'
          }`}>
            {bundle.ok
              ? <CheckCircle size={18} className="text-[#16a34a] flex-shrink-0" />
              : <AlertCircle size={18} className="text-brand-peach flex-shrink-0" />
            }
            <span className="font-semibold text-brand-navy text-sm">
              {bundle.ok ? 'All thresholds OK' : 'Threshold warnings'}
            </span>
            {bundle.health_hints.length > 0 && (
              <span className="text-brand-slate text-sm">{bundle.health_hints.join(' · ')}</span>
            )}
          </div>
        )}

        {error && (
          <div className="bg-white shadow-sm border border-brand-salmon/30 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle size={18} className="text-brand-salmon flex-shrink-0" />
            <p className="text-brand-salmon text-sm">{error}</p>
          </div>
        )}

        {/* KPI row */}
        {sn && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <Stat label="Total calls" value={sn.total_calls} sub={`${sn.fulfilled_calls} fulfilled`} />
            <Stat label="Active now" value={sn.active_calls} color="text-brand-pink" />
            <Stat
              label="Task success"
              value={sn.task_success_rate != null ? `${sn.task_success_rate}%` : '—'}
              color={successColor(sn.task_success_rate)}
            />
            <Stat
              label="P95 latency"
              value={sn.latency_p95_ms != null ? `${sn.latency_p95_ms}ms` : '—'}
              sub={sn.latency_p50_ms != null ? `P50: ${sn.latency_p50_ms}ms` : undefined}
              color={p95Color(sn.latency_p95_ms)}
            />
            <Stat
              label="P50 latency"
              value={sn.latency_p50_ms != null ? `${sn.latency_p50_ms}ms` : '—'}
            />
          </div>
        )}

        {/* Pipeline stages */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
          <h2 className="text-lg font-bold text-brand-navy mb-6 flex items-center gap-2">
            <Activity size={17} className="text-brand-pink" />
            Pipeline Stages
          </h2>
          <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2">
            {PIPELINE_STAGES.map((stage, i) => (
              <div key={stage.id} className="flex items-center gap-2 flex-shrink-0">
                <div className="flex flex-col items-center gap-2 min-w-[100px]">
                  <div className="w-14 h-14 rounded-xl bg-brand-cream border border-[#e8d8d2] flex items-center justify-center">
                    <stage.icon size={24} className={stage.color} />
                  </div>
                  <span className="text-xs text-brand-slate text-center leading-tight">{stage.label}</span>
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <ArrowRight size={16} className="text-brand-muted flex-shrink-0 mb-5" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Distributions row */}
        {sn && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Tool distribution */}
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
              <h3 className="text-sm font-semibold text-brand-navy mb-4 flex items-center gap-2">
                <Wrench size={15} className="text-brand-pink" />
                Tool calls (top)
              </h3>
              {topEntries(sn.tool_call_distribution).length === 0 ? (
                <p className="text-brand-muted text-xs">No tool invocations yet.</p>
              ) : (
                <div className="space-y-2">
                  {topEntries(sn.tool_call_distribution).map(([name, count]) => (
                    <div key={name} className="flex items-center gap-2">
                      <span className="flex-1 text-xs font-mono text-brand-navy truncate">{name}</span>
                      <div className="flex items-center gap-1.5">
                        <div
                          className="h-1.5 rounded-full bg-brand-pink"
                          style={{
                            width: `${Math.max(8, Math.round((count / (topEntries(sn.tool_call_distribution)[0]?.[1] ?? 1)) * 80))}px`,
                          }}
                        />
                        <span className="text-xs font-bold text-brand-pink w-8 text-right">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* End reason distribution */}
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
              <h3 className="text-sm font-semibold text-brand-navy mb-4 flex items-center gap-2">
                <PhoneOff size={15} className="text-brand-pink" />
                End reasons
              </h3>
              {topEntries(sn.end_reason_distribution).length === 0 ? (
                <p className="text-brand-muted text-xs">No ended calls yet.</p>
              ) : (
                <div className="space-y-2">
                  {topEntries(sn.end_reason_distribution).map(([reason, count]) => (
                    <div key={reason} className="flex items-center gap-2">
                      <span className="flex-1 text-xs font-mono text-brand-navy truncate">{reason}</span>
                      <span className="text-xs font-bold text-brand-pink w-8 text-right">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Intent distribution */}
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
              <h3 className="text-sm font-semibold text-brand-navy mb-4 flex items-center gap-2">
                <Zap size={15} className="text-brand-pink" />
                Intent distribution
              </h3>
              {topEntries(sn.intent_distribution).length === 0 ? (
                <p className="text-brand-muted text-xs">No calls yet.</p>
              ) : (
                <div className="space-y-2">
                  {topEntries(sn.intent_distribution).map(([intent, count]) => {
                    const pct = sn.total_calls > 0 ? Math.round((count / sn.total_calls) * 100) : 0;
                    return (
                      <div key={intent} className="flex items-center gap-2">
                        <span className="flex-1 text-xs text-brand-navy capitalize truncate">{intent}</span>
                        <span className="text-xs text-brand-muted w-8 text-right">{pct}%</span>
                        <span className="text-xs font-bold text-brand-pink w-6 text-right">{count}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Source / brain breakdown */}
        {sn && Object.keys(sn.source_distribution ?? {}).length > 0 && (
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <h3 className="text-sm font-semibold text-brand-navy mb-3">Call sources</h3>
            <div className="flex flex-wrap gap-4">
              {Object.entries(sn.source_distribution).map(([src, n]) => (
                <div key={src} className="flex items-center gap-2 text-sm">
                  <span className="capitalize text-brand-navy font-medium">{src}</span>
                  <span className="px-2 py-0.5 bg-brand-cream rounded text-brand-pink font-bold text-xs">{n}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

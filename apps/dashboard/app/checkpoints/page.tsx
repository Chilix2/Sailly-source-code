'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck, ShieldAlert, ShieldX, CheckCircle2, AlertTriangle, XCircle, Info,
  RefreshCw, Server, Database, Bot, ChevronDown, ChevronRight, Clock,
  Phone, MessageSquare, Wrench, AlertOctagon, FileText, Activity,
} from 'lucide-react';

interface CheckpointDetail {
  name: string;
  status: 'passed' | 'warning' | 'failed' | 'alert' | 'info';
  detail: string;
}

interface CheckpointPhase {
  status: string;
  label: string;
  details: CheckpointDetail[];
}

interface CallCheckpoint {
  call_sid: string;
  started_at: string;
  duration_seconds: number;
  outcome: string;
  quality_score: number;
  pre_call: string;
  during_call: string;
  post_call: string;
  transcript_count: number;
  tool_count: number;
  emergency: boolean;
  escalated: boolean;
}

interface AuditScenario {
  call_sid: string;
  composite_score: number;
  weakest_dimension: string;
  weakest_score: number;
  issues: string[];
  timestamp: string;
}

interface SystemData {
  system_health: { database: boolean; python_backend: boolean; dashboard: boolean };
  checkpoint_summary: {
    total_recent: number; transcripts_captured: number; tools_executed: number;
    quality_evaluated: number; analytics_completed: number; emergencies: number;
    escalations: number; short_calls: number; audit_scenarios_generated: number;
  };
  recent_calls: CallCheckpoint[];
  audit_scenarios: AuditScenario[];
  daily_reports: { file: string; date: string; avgScore: number | null; lines: number }[];
}

interface CallDetail {
  call_sid: string;
  overall_status: string;
  call_summary: any;
  checkpoints: { pre_call: CheckpointPhase; during_call: CheckpointPhase; post_call: CheckpointPhase };
}

const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  passed: { icon: CheckCircle2, color: 'text-[#16a34a]', bg: 'bg-green-500/10 border-green-500/30', label: 'Passed' },
  warning: { icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30', label: 'Warning' },
  failed: { icon: XCircle, color: 'text-brand-salmon', bg: 'bg-red-500/10 border-brand-salmon/30', label: 'Failed' },
  alert: { icon: AlertOctagon, color: 'text-brand-salmon', bg: 'bg-red-600/10 border-brand-salmon/30', label: 'Alert' },
  info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30', label: 'Info' },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.info;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${cfg.bg} ${cfg.color}`}>
      <Icon size={12} /> {cfg.label}
    </span>
  );
}

function PhaseCard({ phase, expanded, onToggle }: { phase: CheckpointPhase; expanded: boolean; onToggle: () => void }) {
  const cfg = STATUS_CONFIG[phase.status] || STATUS_CONFIG.info;
  const Icon = cfg.icon;
  return (
    <div className={`border rounded-lg ${cfg.bg}`}>
      <button onClick={onToggle} className="w-full flex items-center gap-3 p-4 text-left">
        <Icon size={20} className={cfg.color} />
        <span className="flex-1 font-semibold text-brand-navy">{phase.label}</span>
        <StatusBadge status={phase.status} />
        {expanded ? <ChevronDown size={16} className="text-brand-slate" /> : <ChevronRight size={16} className="text-brand-slate" />}
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          {phase.details.map((d, i) => {
            const dc = STATUS_CONFIG[d.status] || STATUS_CONFIG.info;
            const DIcon = dc.icon;
            return (
              <div key={i} className="flex items-start gap-2 py-1.5 border-t border-brand-cream">
                <DIcon size={14} className={`mt-0.5 shrink-0 ${dc.color}`} />
                <div className="min-w-0">
                  <span className="text-sm font-medium text-brand-navy">{d.name}</span>
                  <p className="text-xs text-brand-slate break-all">{d.detail}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function CheckpointsPage() {
  const [data, setData] = useState<SystemData | null>(null);
  const [callDetail, setCallDetail] = useState<CallDetail | null>(null);
  const [selectedCall, setSelectedCall] = useState<string | null>(null);
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set(['pre_call', 'during_call', 'post_call']));
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/checkpoints');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); const iv = setInterval(fetchData, 30000); return () => clearInterval(iv); }, [fetchData]);

  const loadCallDetail = async (callSid: string) => {
    setSelectedCall(callSid);
    setDetailLoading(true);
    try {
      const res = await fetch(`/api/dashboard/checkpoints/${callSid}`);
      const json = await res.json();
      setCallDetail(json);
    } catch {
      setCallDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const togglePhase = (phase: string) => {
    setExpandedPhases(prev => {
      const next = new Set(prev);
      next.has(phase) ? next.delete(phase) : next.add(phase);
      return next;
    });
  };

  if (loading) return (
    <div className="flex items-center justify-center h-96">
      <RefreshCw size={24} className="animate-spin text-brand-pink" />
    </div>
  );

  if (error) return (
    <div className="max-w-xl mx-auto mt-20 p-6 bg-red-500/10 border border-brand-salmon/30 rounded-lg text-center">
      <XCircle size={32} className="mx-auto mb-3 text-brand-salmon" />
      <p className="text-brand-salmon">{error}</p>
      <button onClick={fetchData} className="mt-4 px-4 py-2 bg-brand-pink text-black rounded font-medium">Retry</button>
    </div>
  );

  if (!data) return null;
  const s = data.checkpoint_summary;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-brand-navy flex items-center gap-3">
            <ShieldCheck size={28} className="text-brand-pink" /> Call Checkpoints
          </h1>
          <p className="text-brand-slate mt-1">Pre-call, during-call, and post-call monitoring for every call</p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 bg-brand-cream border border-[#e8d8d2] rounded-lg text-sm text-brand-navy hover:bg-[#dfcdc7] transition">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* System Health */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Database', ok: data.system_health.database, icon: Database },
          { label: 'Voice Agent', ok: data.system_health.python_backend, icon: Bot },
          { label: 'Dashboard', ok: data.system_health.dashboard, icon: Server },
        ].map(h => (
          <div key={h.label} className={`p-4 rounded-lg border ${h.ok ? 'bg-green-500/5 border-green-500/20' : 'bg-red-500/10 border-brand-salmon/30'}`}>
            <div className="flex items-center gap-3">
              <h.icon size={18} className={h.ok ? 'text-[#16a34a]' : 'text-brand-salmon'} />
              <span className="text-sm font-medium text-brand-navy">{h.label}</span>
              <span className={`ml-auto text-xs font-bold ${h.ok ? 'text-[#16a34a]' : 'text-brand-salmon'}`}>{h.ok ? 'ONLINE' : 'OFFLINE'}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Checkpoint Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Recent Calls', value: s.total_recent, icon: Phone, accent: false },
          { label: 'Transcripts OK', value: `${s.transcripts_captured}/${s.total_recent}`, icon: MessageSquare, accent: s.transcripts_captured === s.total_recent },
          { label: 'Quality Evals', value: `${s.quality_evaluated}/${s.total_recent}`, icon: Activity, accent: s.quality_evaluated === s.total_recent },
          { label: 'Analytics Done', value: `${s.analytics_completed}/${s.total_recent}`, icon: FileText, accent: s.analytics_completed === s.total_recent },
          { label: 'Tools Executed', value: s.tools_executed, icon: Wrench, accent: false },
          { label: 'Emergencies', value: s.emergencies, icon: AlertOctagon, accent: false },
          { label: 'Escalations', value: s.escalations, icon: AlertTriangle, accent: false },
          { label: 'Audit Flags', value: s.audit_scenarios_generated, icon: ShieldAlert, accent: false },
        ].map(m => (
          <div key={m.label} className="p-4 bg-white shadow-sm border border-brand-cream rounded-lg">
            <div className="flex items-center gap-2 text-xs text-brand-muted uppercase tracking-wider mb-2">
              <m.icon size={12} /> {m.label}
            </div>
            <p className={`text-2xl font-bold ${m.accent ? 'text-[#16a34a]' : m.label === 'Emergencies' && (m.value as number) > 0 ? 'text-brand-salmon' : 'text-brand-navy'}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Calls Checkpoint Table */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg">
          <div className="p-4 border-b border-brand-cream">
            <h2 className="text-lg font-semibold text-brand-navy flex items-center gap-2"><Clock size={16} /> Recent Call Checkpoints</h2>
          </div>
          <div className="divide-y divide-brand-cream max-h-[500px] overflow-y-auto">
            {data.recent_calls.map(c => {
              const callType = c.call_sid.startsWith('demo-') ? 'Demo Call'
                : c.call_sid.startsWith('browser-') ? 'Browser Demo'
                : c.call_sid.startsWith('CA') ? 'Live Call (Twilio)'
                : c.call_sid.startsWith('val-') ? 'Validation' : 'Unknown';
              const callTypeColor = c.call_sid.startsWith('demo-') ? 'bg-blue-50 text-blue-700 border-blue-200'
                : c.call_sid.startsWith('browser-') ? 'bg-purple-50 text-purple-700 border-purple-200'
                : c.call_sid.startsWith('CA') ? 'bg-green-50 text-[#16a34a] border-green-200'
                : c.call_sid.startsWith('val-') ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-gray-50 text-gray-600 border-gray-200';
              const timeStr = c.started_at
                ? new Date(c.started_at).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
                : '—';
              const durMin = Math.floor(c.duration_seconds / 60);
              const durSec = c.duration_seconds % 60;
              const durStr = durMin > 0 ? `${durMin}m ${durSec}s` : `${durSec}s`;

              return (
                <button
                  key={c.call_sid}
                  onClick={() => loadCallDetail(c.call_sid)}
                  className={`w-full text-left p-3 hover:bg-[#ecd8d3] transition ${selectedCall === c.call_sid ? 'bg-[#ecd8d3] border-l-2 border-l-brand-pink' : ''}`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${callTypeColor}`}>{callType}</span>
                    <span className="text-xs text-brand-muted">{timeStr}</span>
                    <span className="text-xs font-mono text-brand-muted ml-auto">{durStr}</span>
                    {c.emergency && <span className="text-[10px] px-1 py-0.5 bg-red-100 text-brand-salmon font-bold rounded">EMERGENCY</span>}
                    {c.escalated && <span className="text-[10px] px-1 py-0.5 bg-amber-100 text-amber-600 font-bold rounded">ESCALATED</span>}
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-brand-navy">{c.call_sid}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={c.pre_call} />
                    <span className="text-brand-muted">→</span>
                    <StatusBadge status={c.during_call} />
                    <span className="text-brand-muted">→</span>
                    <StatusBadge status={c.post_call} />
                    <span className="ml-auto text-xs text-brand-slate">{c.outcome}</span>
                    <span className={`text-xs font-bold ${c.quality_score >= 7 ? 'text-[#16a34a]' : c.quality_score >= 5 ? 'text-amber-500' : 'text-brand-salmon'}`}>
                      Q{c.quality_score.toFixed(1)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 text-[10px] text-brand-muted">
                    <span className="flex items-center gap-0.5"><MessageSquare size={9} /> {c.transcript_count} turns</span>
                    <span className="flex items-center gap-0.5"><Wrench size={9} /> {c.tool_count} tools</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Call Detail Panel */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg">
          <div className="p-4 border-b border-brand-cream">
            <h2 className="text-lg font-semibold text-brand-navy flex items-center gap-2"><ShieldCheck size={16} /> Checkpoint Detail</h2>
          </div>
          <div className="p-4">
            {!selectedCall && (
              <div className="text-center py-12 text-brand-muted">
                <ShieldCheck size={40} className="mx-auto mb-3 opacity-30" />
                <p>Select a call to view checkpoint details</p>
              </div>
            )}
            {detailLoading && (
              <div className="text-center py-12"><RefreshCw size={24} className="mx-auto animate-spin text-brand-pink" /></div>
            )}
            {callDetail && !detailLoading && (() => {
              const sid = callDetail.call_sid;
              const detailType = sid.startsWith('demo-') ? 'Demo Call'
                : sid.startsWith('browser-') ? 'Browser Demo'
                : sid.startsWith('CA') ? 'Live Call (Twilio)'
                : sid.startsWith('val-') ? 'Validation' : 'Unknown';
              const sum = callDetail.call_summary;
              return (
              <div className="space-y-4">
                <div className="pb-3 border-b border-brand-cream space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <StatusBadge status={callDetail.overall_status} />
                    <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-brand-cream text-brand-navy">{detailType}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-brand-muted">Call ID:</span> <span className="font-mono text-brand-navy">{sid}</span></div>
                    <div><span className="text-brand-muted">Duration:</span> <span className="text-brand-navy">{sum.duration_seconds}s</span></div>
                    <div><span className="text-brand-muted">Outcome:</span> <span className="text-brand-navy">{sum.outcome}</span></div>
                    <div><span className="text-brand-muted">Quality:</span> <span className="font-bold text-brand-navy">{(sum.quality_score * 10).toFixed(1)}/10</span></div>
                  </div>
                </div>
                {(['pre_call', 'during_call', 'post_call'] as const).map(phase => (
                  <PhaseCard
                    key={phase}
                    phase={callDetail.checkpoints[phase]}
                    expanded={expandedPhases.has(phase)}
                    onToggle={() => togglePhase(phase)}
                  />
                ))}
              </div>
              );
            })()}
          </div>
        </div>
      </div>

      {/* Audit Scenarios */}
      {data.audit_scenarios.length > 0 && (
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg">
          <div className="p-4 border-b border-brand-cream">
            <h2 className="text-lg font-semibold text-brand-navy flex items-center gap-2">
              <ShieldAlert size={16} className="text-amber-400" /> Audit Flags — Calls Needing Attention
            </h2>
          </div>
          <div className="divide-y divide-brand-cream">
            {data.audit_scenarios.map((s, i) => (
              <div key={i} className="p-4 flex items-start gap-4">
                <div className={`shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold ${s.composite_score >= 75 ? 'bg-green-500/10 text-[#16a34a]' : s.composite_score >= 50 ? 'bg-amber-500/10 text-amber-600' : 'bg-red-500/10 text-brand-salmon'}`}>
                  {s.composite_score}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <button onClick={() => loadCallDetail(s.call_sid)} className="text-sm font-mono text-brand-pink hover:underline">{s.call_sid.slice(0, 24)}...</button>
                    <span className="text-xs text-brand-muted">{new Date(s.timestamp).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })}</span>
                  </div>
                  <p className="text-sm text-brand-slate mt-1">Weakest: <span className="text-amber-600 font-medium">{s.weakest_dimension}</span> ({s.weakest_score}/100)</p>
                  {s.issues.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {s.issues.map((issue, j) => (
                        <span key={j} className="text-xs px-2 py-0.5 bg-amber-100 border border-amber-200 text-amber-700 rounded">{issue}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily Reports */}
      {data.daily_reports.length > 0 && (
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
          <h2 className="text-lg font-semibold text-brand-navy mb-3 flex items-center gap-2"><FileText size={16} /> Daily Audit Reports</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {data.daily_reports.map(r => (
              <div key={r.file} className="p-3 bg-brand-cream border border-[#e8d8d2] rounded-lg">
                <p className="text-sm font-medium text-brand-navy">{r.date}</p>
                <p className="text-xl font-bold text-brand-pink">{r.avgScore !== null ? r.avgScore.toFixed(1) : '—'}</p>
                <p className="text-xs text-brand-muted">{r.lines} lines</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

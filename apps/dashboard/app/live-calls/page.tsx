'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Phone,
  PhoneOff,
  Clock,
  RefreshCw,
  AlertCircle,
  Activity,
  CheckCircle,
  XCircle,
  Zap,
} from 'lucide-react';

interface DashboardCall {
  call_sid: string;
  caller_number: string;
  started_at: string;
  duration_seconds: number;
  quality_score: number;
  outcome: string;
  status?: string;
  cost_usd?: number;
  source?: string;
}

interface OverviewData {
  totalCallsToday: number;
  activeNow: number;
  avgDurationToday: string;
  qualityScoreToday: number;
  costToday: number;
  resolutionRate: number;
  avgLatency: number;
  escalatedToday: number;
}

export default function LiveCallsPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [calls, setCalls] = useState<DashboardCall[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [overviewRes, callsRes] = await Promise.all([
        fetch('/api/dashboard/overview'),
        fetch('/api/dashboard/calls?limit=50'),
      ]);
      if (overviewRes.ok) {
        const data = await overviewRes.json();
        setOverview(data);
      }
      if (callsRes.ok) {
        const data = await callsRes.json();
        if (Array.isArray(data.calls)) setCalls(data.calls);
        else if (Array.isArray(data)) setCalls(data);
      }
      setLastUpdated(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const iv = setInterval(loadData, 10_000);
    return () => clearInterval(iv);
  }, [loadData]);

  function qualityColor(score: number) {
    if (score >= 7.5) return 'text-[#16a34a]';
    if (score >= 5) return 'text-brand-peach';
    return 'text-brand-salmon';
  }

  function formatDuration(secs: number) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-brand-navy mb-1">Live Calls</h1>
            <p className="text-brand-slate text-sm">
              Real-time pipeline monitoring — 10s auto-refresh
              {lastUpdated && (
                <span className="ml-2 text-brand-muted">
                  · Updated {lastUpdated.toLocaleTimeString('de-DE')}
                </span>
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

        {error && (
          <div className="bg-white shadow-sm border border-brand-salmon/30 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle size={18} className="text-brand-salmon flex-shrink-0" />
            <p className="text-brand-salmon text-sm">{error}</p>
          </div>
        )}

        {/* KPI cards */}
        {overview && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
              <p className="text-xs text-brand-slate mb-1 uppercase tracking-wide">Active Now</p>
              <div className="flex items-center gap-2">
                {overview.activeNow > 0 ? (
                  <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center">
                    <Phone size={16} className="text-[#16a34a]" />
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-brand-cream flex items-center justify-center">
                    <PhoneOff size={16} className="text-brand-muted" />
                  </div>
                )}
                <p className="text-3xl font-bold text-brand-navy">{overview.activeNow}</p>
              </div>
            </div>

            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
              <p className="text-xs text-brand-slate mb-1 uppercase tracking-wide">Calls Today</p>
              <p className="text-3xl font-bold text-brand-pink">{overview.totalCallsToday}</p>
            </div>

            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
              <p className="text-xs text-brand-slate mb-1 uppercase tracking-wide">Resolution Rate</p>
              <p className={`text-3xl font-bold ${overview.resolutionRate >= 80 ? 'text-[#16a34a]' : overview.resolutionRate >= 60 ? 'text-brand-peach' : 'text-brand-salmon'}`}>
                {overview.resolutionRate}%
              </p>
            </div>

            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
              <p className="text-xs text-brand-slate mb-1 uppercase tracking-wide">Avg Latency</p>
              <p className="text-3xl font-bold text-brand-navy">{overview.avgLatency}ms</p>
            </div>

            <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
              <p className="text-xs text-brand-slate mb-1 uppercase tracking-wide">Quality</p>
              <p className={`text-3xl font-bold ${qualityColor(overview.qualityScoreToday)}`}>
                {overview.qualityScoreToday.toFixed(1)}
              </p>
              <p className="text-xs text-brand-muted mt-1">/10</p>
            </div>
          </div>
        )}

        {/* Calls table */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-brand-cream flex items-center justify-between">
            <h2 className="text-base font-bold text-brand-navy flex items-center gap-2">
              <Activity size={16} className="text-brand-pink" />
              Recent Calls
            </h2>
            <span className="text-xs text-brand-muted">{calls.length} rows · click for details</span>
          </div>

          {loading && calls.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw size={20} className="animate-spin text-brand-pink" />
            </div>
          ) : calls.length === 0 ? (
            <p className="text-brand-muted text-sm py-8 text-center">
              No calls recorded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-brand-cream border-b border-brand-cream">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Time</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Caller</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Duration</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Quality</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Outcome</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate">Cost</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-brand-slate"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-cream">
                  {calls.map((c) => {
                    const time = c.started_at
                      ? new Date(c.started_at).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
                      : '—';
                    return (
                      <tr
                        key={c.call_sid}
                        className="hover:bg-[#ecd8d3] transition cursor-pointer"
                        onClick={() => router.push(`/calls?id=${encodeURIComponent(c.call_sid)}`)}
                      >
                        <td className="px-4 py-3 text-brand-navy text-xs font-mono">{time}</td>
                        <td className="px-4 py-3 text-brand-navy text-xs">{c.caller_number || '—'}</td>
                        <td className="px-4 py-3 text-brand-navy text-xs flex items-center gap-1">
                          <Clock size={12} className="text-brand-muted" />
                          {formatDuration(c.duration_seconds)}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-bold ${qualityColor(c.quality_score)}`}>
                            {c.quality_score?.toFixed(1) || '—'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {c.outcome === 'completed' || c.outcome === 'resolved' ? (
                            <span className="flex items-center gap-1 text-xs text-[#16a34a]">
                              <CheckCircle size={13} /> {c.outcome}
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-xs text-brand-muted">
                              <XCircle size={13} /> {c.outcome || '—'}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-brand-muted text-xs">
                          {c.cost_usd != null ? `€${c.cost_usd.toFixed(3)}` : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <Zap size={13} className="text-brand-pink" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

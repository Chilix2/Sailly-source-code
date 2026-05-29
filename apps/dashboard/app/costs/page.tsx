'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  DollarSign,
  Phone,
  TrendingUp,
  Calendar,
  Download,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface DailyBreakdown {
  date: string;
  gemini: number;
  twilio: number;
  total: number;
  calls: number;
}

interface RecentCall {
  id: number;
  call_sid: string;
  started_at: string;
  duration_seconds: number;
  gemini: number;
  twilio: number;
  total: number;
  outcome: string;
}

interface CostsData {
  todaySpend: number;
  todayCalls: number;
  weekSpend: number;
  weekCalls: number;
  allTimeSpend: number;
  allTimeCalls: number;
  avgCostPerCall: number;
  dailyBreakdown: DailyBreakdown[];
  recentCalls: RecentCall[];
}

const fmt = (n: number) => n.toFixed(2);
const fmtEur = (n: number) => `€${fmt(n)}`;

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
}

export default function CostsPage() {
  const [data, setData] = useState<CostsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCosts = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard/costs');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: CostsData = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCosts();
    const interval = setInterval(fetchCosts, 30_000);
    return () => clearInterval(interval);
  }, [fetchCosts]);

  const handleExport = () => {
    if (!data) return;
    const rows = [
      ['Call ID', 'SID', 'Date', 'Duration', 'Gemini (€)', 'Twilio (€)', 'Total (€)', 'Outcome'],
      ...data.recentCalls.map((c) => [
        c.id,
        c.call_sid,
        formatDateTime(c.started_at),
        formatDuration(c.duration_seconds),
        fmt(c.gemini),
        fmt(c.twilio),
        fmt(c.total),
        c.outcome,
      ]),
    ]
      .map((r) => r.map((v) => `"${v}"`).join(','))
      .join('\n');
    const blob = new Blob([rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `costs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <div className="flex items-center gap-3 text-brand-slate">
          <RefreshCw size={20} className="animate-spin" />
          <span>Loading cost data…</span>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <div className="bg-[#fff0ee] border border-[#ffd8d0] rounded-lg p-6 max-w-md text-center space-y-3">
          <AlertCircle size={32} className="text-brand-salmon mx-auto" />
          <p className="text-brand-salmon font-semibold">Failed to load costs</p>
          <p className="text-brand-salmon text-sm">{error}</p>
          <button
            onClick={fetchCosts}
            className="px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] text-brand-navy rounded-lg text-sm transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const chartData = data.dailyBreakdown.map((d) => ({
    ...d,
    label: formatDate(d.date),
  }));

  const providerData = data.dailyBreakdown.map((d) => ({
    label: formatDate(d.date),
    Gemini: d.gemini,
    Twilio: d.twilio,
  }));

  const tooltipStyle = {
    backgroundColor: '#18181b',
    border: '1px solid #3f3f46',
    borderRadius: '6px',
  };

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-brand-navy">Cost Dashboard</h1>
            <p className="text-brand-slate mt-1">Per-call cost tracking &amp; provider breakdown</p>
          </div>
          {error && (
            <div className="flex items-center gap-2 text-yellow-400 text-xs bg-[#fff8ea] border border-[#ffe4cc] rounded-lg px-3 py-2">
              <AlertCircle size={14} />
              Refresh failed — showing stale data
            </div>
          )}
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-brand-muted uppercase tracking-wide">Today&apos;s Spend</p>
                <p className="text-2xl font-bold text-brand-navy mt-2">{fmtEur(data.todaySpend)}</p>
                <p className="text-xs text-brand-slate mt-1">{data.todayCalls} calls</p>
              </div>
              <DollarSign size={20} className="text-zinc-700" />
            </div>
          </div>

          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-brand-muted uppercase tracking-wide">7-Day Spend</p>
                <p className="text-2xl font-bold text-brand-navy mt-2">{fmtEur(data.weekSpend)}</p>
                <p className="text-xs text-brand-slate mt-1">{data.weekCalls} calls</p>
              </div>
              <Calendar size={20} className="text-zinc-700" />
            </div>
          </div>

          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-brand-muted uppercase tracking-wide">Avg Cost / Call</p>
                <p className="text-2xl font-bold text-brand-pink mt-2">{fmtEur(data.avgCostPerCall)}</p>
                <p className="text-xs text-brand-slate mt-1">across all calls</p>
              </div>
              <TrendingUp size={20} className="text-zinc-700" />
            </div>
          </div>

          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-brand-muted uppercase tracking-wide">All-Time</p>
                <p className="text-2xl font-bold text-brand-navy mt-2">{fmtEur(data.allTimeSpend)}</p>
                <p className="text-xs text-brand-slate mt-1">{data.allTimeCalls} calls total</p>
              </div>
              <Phone size={20} className="text-zinc-700" />
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Cost Trend */}
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
            <h3 className="text-sm font-semibold text-brand-navy mb-4">Daily Cost Trend</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                <XAxis dataKey="label" stroke="#71717a" tick={{ fontSize: 12 }} />
                <YAxis stroke="#71717a" tick={{ fontSize: 12 }} tickFormatter={(v) => `€${v}`} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  labelStyle={{ color: '#fafafa' }}
                  formatter={(value: number) => [`€${fmt(value)}`, undefined]}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="total"
                  name="Total"
                  stroke="hsl(192, 100%, 50%)"
                  strokeWidth={2}
                  dot={{ fill: 'hsl(192, 100%, 50%)', r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="gemini"
                  name="Gemini"
                  stroke="#a855f7"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="twilio"
                  name="Twilio"
                  stroke="#3b82f6"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Provider Breakdown */}
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
            <h3 className="text-sm font-semibold text-brand-navy mb-4">Provider Breakdown (Gemini vs Twilio)</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={providerData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                <XAxis dataKey="label" stroke="#71717a" tick={{ fontSize: 12 }} />
                <YAxis stroke="#71717a" tick={{ fontSize: 12 }} tickFormatter={(v) => `€${v}`} />
                <Tooltip
                  contentStyle={tooltipStyle}
                  labelStyle={{ color: '#fafafa' }}
                  formatter={(value: number) => [`€${fmt(value)}`, undefined]}
                />
                <Legend />
                <Bar dataKey="Gemini" fill="#a855f7" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Twilio" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Per-Call Cost Table */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg overflow-hidden">
          <div className="flex items-center justify-between p-6 border-b border-brand-cream">
            <h3 className="text-sm font-semibold text-brand-navy">Recent Calls — Cost Breakdown</h3>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy text-sm transition"
            >
              <Download size={16} />
              Export CSV
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-brand-cream border-b border-brand-cream">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">#</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Outcome</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-brand-slate">Gemini</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-brand-slate">Twilio</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-brand-pink">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {data.recentCalls.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-brand-muted">
                      No calls recorded yet
                    </td>
                  </tr>
                ) : (
                  data.recentCalls.map((call) => (
                    <tr key={call.id} className="hover:bg-[#ecd8d3] transition-colors">
                      <td className="px-6 py-3 text-brand-muted font-mono text-xs">{call.id}</td>
                      <td className="px-6 py-3 text-brand-navy text-xs">
                        {formatDateTime(call.started_at)}
                      </td>
                      <td className="px-6 py-3 text-brand-navy">
                        {formatDuration(call.duration_seconds)}
                      </td>
                      <td className="px-6 py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            call.outcome === 'order'
                              ? 'bg-[#f0fdf4] text-[#16a34a]'
                              : call.outcome === 'reservation'
                                ? 'bg-blue-950/50 text-brand-slate'
                                : 'bg-brand-cream text-brand-slate'
                          }`}
                        >
                          {call.outcome}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-right text-brand-slate font-mono text-xs">
                        {fmtEur(call.gemini)}
                      </td>
                      <td className="px-6 py-3 text-right text-brand-slate font-mono text-xs">
                        {fmtEur(call.twilio)}
                      </td>
                      <td className="px-6 py-3 text-right text-brand-pink font-semibold font-mono text-xs">
                        {fmtEur(call.total)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

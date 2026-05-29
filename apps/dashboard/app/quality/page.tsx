'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  BarChart3,
  Phone,
  Loader2,
  ArrowDown,
  ArrowUp,
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
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface TrendPoint {
  date: string;
  score: number;
  calls: number;
}

interface Evaluation {
  call_sid: string;
  score: number;
  issues: string[];
  tool_usage_score: number;
  greeting_score: number;
  resolution_score: number;
}

interface LowQualityCall {
  id: number;
  call_sid: string;
  quality_score: number;
  outcome: string;
  duration_seconds: number;
  started_at: string;
  issues: string[];
}

interface QualityData {
  avgScore: number;
  totalScored: number;
  minScore: number;
  maxScore: number;
  passRate: number;
  passed: number;
  failed: number;
  trends: TrendPoint[];
  evaluations: Evaluation[];
  lowQualityCalls: LowQualityCall[];
}

function scoreToTen(score: number): string {
  return (score * 10).toFixed(1);
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function QualityPage() {
  const [data, setData] = useState<QualityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        const res = await fetch('/api/dashboard/quality');
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load quality data');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent flex items-center justify-center">
        <div className="flex items-center gap-3 text-brand-slate">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-lg">Loading quality data…</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-transparent flex items-center justify-center">
        <div className="bg-white shadow-sm border border-red-800 rounded-lg p-8 max-w-md text-center">
          <AlertTriangle className="w-10 h-10 text-brand-salmon mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-brand-navy mb-2">Failed to load data</h2>
          <p className="text-brand-slate mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-brand-cream text-brand-navy rounded-lg border border-[#e8d8d2] hover:bg-[#dfcdc7] transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const trendChartData = data.trends.map((t) => ({
    date: t.date,
    score: +(t.score * 10).toFixed(1),
    calls: t.calls,
  }));

  const scoreDistribution = [
    { range: '0-2', count: 0 },
    { range: '2-4', count: 0 },
    { range: '4-6', count: 0 },
    { range: '6-8', count: 0 },
    { range: '8-10', count: 0 },
  ];
  data.evaluations.forEach((ev) => {
    const s = ev.score;
    if (s < 2) scoreDistribution[0].count++;
    else if (s < 4) scoreDistribution[1].count++;
    else if (s < 6) scoreDistribution[2].count++;
    else if (s < 8) scoreDistribution[3].count++;
    else scoreDistribution[4].count++;
  });

  const distColors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#10b981'];

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-brand-navy mb-1">Quality Dashboard</h1>
        <p className="text-brand-slate">
          Call quality scores, trends, and evaluations &mdash; {data.totalScored} calls scored
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-brand-slate text-sm font-medium">Avg Score</span>
            <TrendingUp className="w-4 h-4 text-brand-muted" />
          </div>
          <p className="text-3xl font-bold text-brand-navy">{scoreToTen(data.avgScore)}<span className="text-lg text-brand-muted">/10</span></p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-brand-slate text-sm font-medium">Pass Rate</span>
            <CheckCircle className="w-4 h-4 text-[#16a34a]" />
          </div>
          <p className="text-3xl font-bold text-[#16a34a]">{data.passRate}%</p>
          <p className="text-xs text-brand-muted mt-1">{data.passed} passed / {data.failed} failed</p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-brand-slate text-sm font-medium">Min Score</span>
            <ArrowDown className="w-4 h-4 text-brand-salmon" />
          </div>
          <p className="text-3xl font-bold text-brand-salmon">{scoreToTen(data.minScore)}<span className="text-lg text-brand-muted">/10</span></p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-brand-slate text-sm font-medium">Max Score</span>
            <ArrowUp className="w-4 h-4 text-[#16a34a]" />
          </div>
          <p className="text-3xl font-bold text-[#16a34a]">{scoreToTen(data.maxScore)}<span className="text-lg text-brand-muted">/10</span></p>
        </div>
      </div>

      {/* Trends Chart */}
      <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="w-5 h-5 text-brand-slate" />
          <h2 className="text-lg font-semibold text-brand-navy">Quality Score Trend</h2>
        </div>
        {trendChartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis dataKey="date" stroke="#71717a" tick={{ fontSize: 12 }} />
              <YAxis stroke="#71717a" domain={[0, 10]} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
                itemStyle={{ color: '#a1a1aa' }}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#3b82f6"
                name="Score (/10)"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', r: 4 }}
                activeDot={{ r: 6 }}
              />
              <Line
                type="monotone"
                dataKey="calls"
                stroke="#8b5cf6"
                name="Calls"
                strokeWidth={2}
                dot={{ fill: '#8b5cf6', r: 3 }}
                yAxisId={0}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-brand-muted text-center py-12">No trend data available yet.</p>
        )}
      </div>

      {/* Score Distribution */}
      <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
        <div className="flex items-center gap-2 mb-6">
          <BarChart3 className="w-5 h-5 text-brand-slate" />
          <h2 className="text-lg font-semibold text-brand-navy">Score Distribution</h2>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={scoreDistribution}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="range" stroke="#71717a" tick={{ fontSize: 12 }} />
            <YAxis stroke="#71717a" allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
              labelStyle={{ color: '#fff' }}
              itemStyle={{ color: '#a1a1aa' }}
            />
            <Bar dataKey="count" name="Evaluations" radius={[4, 4, 0, 0]}>
              {scoreDistribution.map((_, i) => (
                <Cell key={i} fill={distColors[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Evaluations Table */}
      <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-brand-navy mb-4">
          Call Evaluations ({data.evaluations.length})
        </h2>
        {data.evaluations.length === 0 ? (
          <p className="text-brand-muted text-center py-8">No evaluations recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-brand-cream text-brand-slate">
                  <th className="text-left py-3 pr-4 font-medium">Call SID</th>
                  <th className="text-right py-3 px-4 font-medium">Overall</th>
                  <th className="text-right py-3 px-4 font-medium">Greeting</th>
                  <th className="text-right py-3 px-4 font-medium">Tool Usage</th>
                  <th className="text-right py-3 px-4 font-medium">Resolution</th>
                  <th className="text-left py-3 pl-4 font-medium">Issues</th>
                </tr>
              </thead>
              <tbody>
                {data.evaluations.map((ev) => (
                  <tr key={ev.call_sid} className="border-b border-brand-cream hover:bg-zinc-800/30">
                    <td className="py-3 pr-4 font-mono text-xs text-brand-navy">
                      {ev.call_sid.length > 20 ? ev.call_sid.slice(0, 20) + '\u2026' : ev.call_sid}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className={`font-semibold ${ev.score >= 7 ? 'text-[#16a34a]' : ev.score >= 4 ? 'text-yellow-400' : 'text-brand-salmon'}`}>
                        {ev.score.toFixed(1)}/10
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-brand-navy">{ev.greeting_score}/10</td>
                    <td className="py-3 px-4 text-right text-brand-navy">{ev.tool_usage_score}/10</td>
                    <td className="py-3 px-4 text-right text-brand-navy">{ev.resolution_score}/10</td>
                    <td className="py-3 pl-4">
                      {ev.issues.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {ev.issues.map((issue, i) => (
                            <span key={i} className="px-2 py-0.5 text-xs bg-red-900/30 text-brand-salmon border border-red-800/50 rounded">
                              {issue}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-brand-muted text-xs">None</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Low Quality Calls */}
      <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-brand-salmon" />
          <h2 className="text-lg font-semibold text-brand-navy">
            Low Quality Calls ({data.lowQualityCalls.length})
          </h2>
        </div>
        {data.lowQualityCalls.length === 0 ? (
          <p className="text-brand-muted text-center py-8">No low-quality calls detected.</p>
        ) : (
          <div className="space-y-3">
            {data.lowQualityCalls.map((call) => (
              <div key={call.id} className="flex items-center gap-4 p-4 bg-brand-cream border border-brand-cream rounded-lg">
                <XCircle className="w-5 h-5 text-brand-salmon shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-xs text-brand-navy truncate">
                      {call.call_sid}
                    </span>
                    <span className="px-2 py-0.5 text-xs rounded bg-[#e8d8d2] text-brand-navy">
                      {call.outcome}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-brand-muted">
                    <span className="flex items-center gap-1">
                      <Phone className="w-3 h-3" />
                      {formatDuration(call.duration_seconds)}
                    </span>
                    {call.started_at && (
                      <span>{new Date(call.started_at).toLocaleString()}</span>
                    )}
                    {call.issues.length > 0 && (
                      <span className="text-brand-salmon">{call.issues.join(', ')}</span>
                    )}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-lg font-bold text-brand-salmon">
                    {scoreToTen(call.quality_score)}<span className="text-sm text-brand-muted">/10</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

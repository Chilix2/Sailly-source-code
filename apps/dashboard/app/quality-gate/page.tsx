'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ShieldCheck,
  ShieldX,
  Loader2,
  BarChart3,
  ListChecks,
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
  PieChart,
  Pie,
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

export default function QualityGatePage() {
  const [data, setData] = useState<QualityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSid, setExpandedSid] = useState<string | null>(null);

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
          setError(err instanceof Error ? err.message : 'Failed to load quality gate data');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent flex items-center justify-center">
        <div className="flex items-center gap-3 text-brand-slate">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-lg">Loading quality gate…</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-transparent flex items-center justify-center">
        <div className="bg-white shadow-sm border border-red-800 rounded-lg p-8 max-w-md text-center">
          <AlertTriangle className="w-10 h-10 text-brand-salmon mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-brand-navy mb-2">Quality gate unavailable</h2>
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

  const gatePass = data.passRate >= 70;

  const pieData = [
    { name: 'Passed', value: data.passed, color: '#22c55e' },
    { name: 'Failed', value: data.failed, color: '#ef4444' },
  ];

  const scoreDistribution = [
    { range: '0\u20132', count: 0 },
    { range: '2\u20134', count: 0 },
    { range: '4\u20136', count: 0 },
    { range: '6\u20138', count: 0 },
    { range: '8\u201310', count: 0 },
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

  const subScoreAvgs = data.evaluations.length > 0
    ? {
        greeting: data.evaluations.reduce((s, e) => s + e.greeting_score, 0) / data.evaluations.length,
        toolUsage: data.evaluations.reduce((s, e) => s + e.tool_usage_score, 0) / data.evaluations.length,
        resolution: data.evaluations.reduce((s, e) => s + e.resolution_score, 0) / data.evaluations.length,
      }
    : null;

  const subScoreBarData = subScoreAvgs
    ? [
        { category: 'Greeting', avg: +subScoreAvgs.greeting.toFixed(1) },
        { category: 'Tool Usage', avg: +subScoreAvgs.toolUsage.toFixed(1) },
        { category: 'Resolution', avg: +subScoreAvgs.resolution.toFixed(1) },
      ]
    : [];

  return (
    <div className="min-h-screen bg-transparent p-8">
      {/* Header + Gate Status */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-brand-navy mb-1">Quality Gate</h1>
          <p className="text-brand-slate">
            Deploy readiness based on {data.totalScored} scored calls
          </p>
        </div>
        <div className={`flex items-center gap-3 px-5 py-3 rounded-lg border ${
          gatePass
            ? 'bg-green-950/40 border-green-800 text-[#16a34a]'
            : 'bg-red-950/40 border-red-800 text-brand-salmon'
        }`}>
          {gatePass ? <ShieldCheck className="w-7 h-7" /> : <ShieldX className="w-7 h-7" />}
          <div>
            <p className="text-lg font-bold">{gatePass ? 'GATE PASSED' : 'GATE FAILED'}</p>
            <p className="text-xs opacity-70">{gatePass ? 'Ready to deploy' : 'Quality below threshold'}</p>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <span className="text-brand-slate text-sm font-medium">Pass Rate</span>
          <p className={`text-3xl font-bold mt-2 ${data.passRate >= 70 ? 'text-[#16a34a]' : 'text-brand-salmon'}`}>
            {data.passRate}%
          </p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <span className="text-brand-slate text-sm font-medium">Avg Score</span>
          <p className="text-3xl font-bold text-brand-navy mt-2">
            {scoreToTen(data.avgScore)}<span className="text-lg text-brand-muted">/10</span>
          </p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-[#16a34a]" />
            <span className="text-brand-slate text-sm font-medium">Passed</span>
          </div>
          <p className="text-3xl font-bold text-[#16a34a] mt-2">{data.passed}</p>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
          <div className="flex items-center gap-2">
            <XCircle className="w-4 h-4 text-brand-salmon" />
            <span className="text-brand-slate text-sm font-medium">Failed</span>
          </div>
          <p className="text-3xl font-bold text-brand-salmon mt-2">{data.failed}</p>
        </div>
      </div>

      {/* Pass/Fail Pie + Score Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
          <h2 className="text-lg font-semibold text-brand-navy mb-4">Pass / Fail Breakdown</h2>
          {data.totalScored > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  dataKey="value"
                  paddingAngle={3}
                  stroke="none"
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                  itemStyle={{ color: '#a1a1aa' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-brand-muted text-center py-12">No data yet.</p>
          )}
          <div className="flex justify-center gap-6 mt-2">
            <div className="flex items-center gap-2 text-sm">
              <span className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-brand-slate">Passed ({data.passed})</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="w-3 h-3 rounded-full bg-red-500" />
              <span className="text-brand-slate">Failed ({data.failed})</span>
            </div>
          </div>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-brand-slate" />
            <h2 className="text-lg font-semibold text-brand-navy">Score Distribution</h2>
          </div>
          <ResponsiveContainer width="100%" height={250}>
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
      </div>

      {/* Sub-Score Averages */}
      {subScoreBarData.length > 0 && (
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold text-brand-navy mb-4">Average Sub-Scores</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={subScoreBarData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
              <XAxis type="number" domain={[0, 10]} stroke="#71717a" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="category" stroke="#71717a" width={100} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                labelStyle={{ color: '#fff' }}
                itemStyle={{ color: '#a1a1aa' }}
                formatter={(value: number) => [`${value}/10`, 'Avg']}
              />
              <Bar
                dataKey="avg"
                name="Average"
                radius={[0, 4, 4, 0]}
                fill="#3b82f6"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Evaluation Details */}
      <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <ListChecks className="w-5 h-5 text-brand-slate" />
          <h2 className="text-lg font-semibold text-brand-navy">
            Evaluation Details ({data.evaluations.length})
          </h2>
        </div>
        {data.evaluations.length === 0 ? (
          <p className="text-brand-muted text-center py-8">No evaluations recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {data.evaluations.map((ev) => {
              const isExpanded = expandedSid === ev.call_sid;
              const passed = ev.score >= 7;
              return (
                <div key={ev.call_sid} className="border border-brand-cream rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedSid(isExpanded ? null : ev.call_sid)}
                    className="w-full flex items-center gap-4 p-4 hover:bg-zinc-800/40 transition-colors text-left"
                  >
                    {passed ? (
                      <CheckCircle className="w-5 h-5 text-[#16a34a] shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-brand-salmon shrink-0" />
                    )}
                    <span className="font-mono text-xs text-brand-navy truncate flex-1">
                      {ev.call_sid}
                    </span>
                    <span className={`text-sm font-bold ${passed ? 'text-[#16a34a]' : 'text-brand-salmon'}`}>
                      {ev.score.toFixed(1)}/10
                    </span>
                    {ev.issues.length > 0 && (
                      <span className="text-xs text-brand-salmon bg-red-900/30 px-2 py-0.5 rounded border border-red-800/50">
                        {ev.issues.length} issue{ev.issues.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </button>
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-2 border-t border-brand-cream bg-[#fcfaf9]">
                      <div className="grid grid-cols-3 gap-4 mb-3">
                        <div>
                          <p className="text-xs text-brand-muted mb-1">Greeting</p>
                          <p className="text-sm font-semibold text-brand-navy">{ev.greeting_score}/10</p>
                        </div>
                        <div>
                          <p className="text-xs text-brand-muted mb-1">Tool Usage</p>
                          <p className="text-sm font-semibold text-brand-navy">{ev.tool_usage_score}/10</p>
                        </div>
                        <div>
                          <p className="text-xs text-brand-muted mb-1">Resolution</p>
                          <p className="text-sm font-semibold text-brand-navy">{ev.resolution_score}/10</p>
                        </div>
                      </div>
                      {ev.issues.length > 0 && (
                        <div>
                          <p className="text-xs text-brand-muted mb-2">Issues</p>
                          <div className="flex flex-wrap gap-1">
                            {ev.issues.map((issue, i) => (
                              <span key={i} className="px-2 py-0.5 text-xs bg-red-900/30 text-brand-salmon border border-red-800/50 rounded">
                                {issue}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

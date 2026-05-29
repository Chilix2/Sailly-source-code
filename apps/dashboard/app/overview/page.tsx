'use client';

import React, { useEffect, useState } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, TrendingDown, Zap, DollarSign, PhoneOff, Clock, BarChart3 } from 'lucide-react';

interface MetricsData {
  totalCallsToday: number;
  activeNow: number;
  avgDurationToday: string;
  qualityScoreToday: number;
  costToday: number;
  resolutionRate: number;
  avgLatency: number;
  escalatedToday: number;
  deltaCallsVsLastWeek: number;
  deltaQualityVsLastWeek: number;
  callVolume7Days: Array<{ date: string; count: number }>;
  qualityTrend7Days: Array<{ date: string; score: number }>;
  recentCalls: Array<{
    id: string;
    call_sid: string;
    caller_number: string;
    started_at: string;
    duration_seconds: number;
    quality_score: number;
    outcome: string;
  }>;
  alerts: Array<{ type: string; message: string; severity: 'info' | 'warning' | 'error' }>;
}

function MetricCard({
  label,
  value,
  subtext,
  icon: Icon,
  delta,
  deltaPositive,
}: {
  label: string;
  value: string | number;
  subtext?: string;
  icon: React.ReactNode;
  delta?: number;
  deltaPositive?: boolean;
}) {
  return (
    <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-bold text-brand-navy uppercase tracking-widest">{label}</p>
          <p className="text-3xl font-black text-brand-navy mt-2">{value}</p>
          {subtext && <p className="text-xs font-semibold text-brand-navy mt-1">{subtext}</p>}
        </div>
        <div className="text-brand-pink">{Icon}</div>
      </div>
      {delta !== undefined && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          {deltaPositive ? (
            <TrendingUp size={14} className="text-[#16a34a]" fill="currentColor" />
          ) : (
            <TrendingDown size={14} className="text-brand-salmon" fill="currentColor" />
          )}
          <span className={deltaPositive ? 'text-[#16a34a]' : 'text-brand-salmon'}>
            {deltaPositive ? '+' : ''}{delta}% vs last week
          </span>
        </div>
      )}
    </div>
  );
}

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        setLoading(true);
        const response = await fetch('/api/dashboard/overview');
        if (!response.ok) throw new Error('Failed to fetch overview');
        const data = await response.json();
        setMetrics(data);
      } catch (err) {
        console.error('Error fetching metrics:', err);
        setError("Failed to load live metrics from backend");
        // Fallback to mock data for demo
        setMetrics({
          totalCallsToday: 47,
          activeNow: 3,
          avgDurationToday: '3m 24s',
          qualityScoreToday: 8.4,
          costToday: 12.4,
          resolutionRate: 92,
          avgLatency: 340,
          escalatedToday: 4,
          deltaCallsVsLastWeek: 12,
          deltaQualityVsLastWeek: 0.3,
          callVolume7Days: [
            { date: 'Mon', count: 42 },
            { date: 'Tue', count: 38 },
            { date: 'Wed', count: 45 },
            { date: 'Thu', count: 52 },
            { date: 'Fri', count: 47 },
            { date: 'Sat', count: 31 },
            { date: 'Sun', count: 28 },
          ],
          qualityTrend7Days: [
            { date: 'Mon', score: 8.2 },
            { date: 'Tue', score: 8.1 },
            { date: 'Wed', score: 8.3 },
            { date: 'Thu', score: 8.5 },
            { date: 'Fri', score: 8.4 },
            { date: 'Sat', score: 8.0 },
            { date: 'Sun', score: 8.1 },
          ],
          recentCalls: [
            {
              id: '1',
              call_sid: 'conv_abc123',
              caller_number: '+49 176 XXXX',
              started_at: new Date(Date.now() - 120000).toISOString(),
              duration_seconds: 252,
              quality_score: 9.1,
              outcome: 'Reservation',
            },
            {
              id: '2',
              call_sid: 'conv_def456',
              caller_number: '+49 152 XXXX',
              started_at: new Date(Date.now() - 240000).toISOString(),
              duration_seconds: 165,
              quality_score: 7.8,
              outcome: 'Info query',
            },
          ],
          alerts: [
            { type: 'quality', message: 'Quality dropped below 7.0 for 2 consecutive calls', severity: 'warning' },
            { type: 'latency', message: 'Gemini API latency spike: 890ms avg (last 15 min)', severity: 'warning' },
          ],
        });
      } finally {
        setLoading(false);
      }
    }

    fetchMetrics();

    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !metrics) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <p className="text-text-muted">Loading Command Center...</p>
      </div>
    );
  }

  if (!metrics) return null;

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-black text-brand-navy">Command Center</h1>
          <p className="font-semibold text-brand-navy mt-1">Real-time voice AI operations overview</p>
        </div>

        {/* Alerts */}
        {metrics.alerts.length > 0 && (
          <div className="space-y-2">
            {metrics.alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`flex gap-3 p-3 rounded-lg border ${
                  alert.severity === 'error'
                    ? 'bg-[#fff0ee] border-[#ffd8d0] text-brand-salmon'
                    : alert.severity === 'warning'
                      ? 'bg-[#fff8ea] border-[#ffe4cc] text-brand-peach'
                      : 'bg-[#f4f7fb] border-[#dce5f0] text-brand-slate'
                }`}
              >
                <AlertCircle size={18} className="flex-shrink-0 mt-0.5" fill="currentColor" />
                <p className="text-sm">{alert.message}</p>
              </div>
            ))}
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Total Calls Today"
            value={metrics.totalCallsToday}
            icon={<BarChart3 size={20} fill="currentColor" />}
            delta={metrics.deltaCallsVsLastWeek}
            deltaPositive={metrics.deltaCallsVsLastWeek > 0}
          />
          <MetricCard
            label="Active Now"
            value={metrics.activeNow}
            icon={<Zap size={20} className="text-brand-pink" fill="currentColor" />}
            subtext="● Live connections"
          />
          <MetricCard
            label="Avg Duration"
            value={metrics.avgDurationToday}
            icon={<Clock size={20} fill="currentColor" />}
          />
          <MetricCard
            label="Quality Score"
            value={metrics.qualityScoreToday.toFixed(1)}
            subtext="/10"
            icon={<BarChart3 size={20} className="text-accent-3" fill="currentColor" />}
            delta={metrics.deltaQualityVsLastWeek * 10}
            deltaPositive={metrics.deltaQualityVsLastWeek > 0}
          />

          <MetricCard
            label="Cost Today"
            value={`€${metrics.costToday.toFixed(2)}`}
            icon={<DollarSign size={20} fill="currentColor" />}
          />
          <MetricCard
            label="Resolution Rate"
            value={`${metrics.resolutionRate}%`}
            icon={<TrendingUp size={20} className="text-accent-3" fill="currentColor" />}
          />
          <MetricCard
            label="Avg Latency"
            value={`${metrics.avgLatency}ms`}
            icon={<Clock size={20} fill="currentColor" />}
          />
          <MetricCard
            label="Escalated"
            value={metrics.escalatedToday}
            icon={<PhoneOff size={20} fill="currentColor" />}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Call Volume */}
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
            <h3 className="text-sm font-semibold text-brand-navy mb-4">Call Volume (7 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={metrics.callVolume7Days}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                <XAxis dataKey="date" stroke="#71717a" />
                <YAxis stroke="#71717a" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '6px' }}
                  labelStyle={{ color: '#fafafa' }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="hsl(192, 100%, 50%)"
                  strokeWidth={2}
                  dot={{ fill: 'hsl(192, 100%, 50%)', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Quality Trend */}
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
            <h3 className="text-sm font-semibold text-brand-navy mb-4">Quality Trend (7 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={metrics.qualityTrend7Days}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                <XAxis dataKey="date" stroke="#71717a" />
                <YAxis stroke="#71717a" domain={[6, 10]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '6px' }}
                  labelStyle={{ color: '#fafafa' }}
                />
                <Area
                  type="monotone"
                  dataKey="score"
                  fill="hsl(160, 85%, 45%)"
                  stroke="hsl(160, 85%, 45%)"
                  fillOpacity={0.2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Calls */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg overflow-hidden">
          <div className="p-6 border-b border-brand-cream">
            <h3 className="text-sm font-semibold text-brand-navy">Recent Calls</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-brand-cream border-b border-brand-cream">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-bold text-brand-navy uppercase tracking-wider">Time</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-brand-navy uppercase tracking-wider">Caller</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-brand-navy uppercase tracking-wider">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-brand-navy uppercase tracking-wider">Quality</th>
                  <th className="px-6 py-3 text-left text-xs font-bold text-brand-navy uppercase tracking-wider">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {metrics.recentCalls.map((call) => (
                  <tr key={call.id} className="hover:bg-[#ecd8d3] transition-colors cursor-pointer">
                    <td className="px-6 py-3 text-brand-navy">
                      {new Date(call.started_at).toLocaleTimeString('de-DE', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-6 py-3 text-brand-navy font-mono text-xs">{call.caller_number}</td>
                    <td className="px-6 py-3 text-brand-navy">
                      {Math.floor(call.duration_seconds / 60)}:{(call.duration_seconds % 60).toString().padStart(2, '0')}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          call.quality_score >= 8
                            ? 'bg-[#f0fdf4] text-[#16a34a]'
                            : call.quality_score >= 6
                              ? 'bg-[#fff8ea] text-brand-peach'
                              : 'bg-[#fff0ee] text-brand-salmon'
                        }`}
                      >
                        {call.quality_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-brand-navy font-semibold text-xs">{call.outcome}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

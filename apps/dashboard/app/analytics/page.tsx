'use client';

import React, { useState, useEffect } from 'react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  BarChart3, TrendingUp, Activity, Clock, DollarSign, Star,
  RefreshCw, AlertCircle,
} from 'lucide-react';

interface AnalyticsData {
  callVolume: { date: string; count: number }[];
  outcomes: { outcome: string; count: number }[];
  sentiments: { sentiment: string; count: number }[];
  durations: { bucket: string; count: number }[];
  costTrend: { date: string; cost: number }[];
  qualityDist: { bucket: string; count: number }[];
}

const CHART_COLORS = [
  '#00d4ff', '#7c3aed', '#00b37e', '#e6a817', '#e63946', '#48bfe3', '#ff6b6b',
];

const SENTIMENT_COLORS: Record<string, string> = {
  positive: '#00b37e',
  neutral: '#00d4ff',
  negative: '#e63946',
  mixed: '#e6a817',
};

function shortDate(d: string) {
  try {
    const dt = new Date(d);
    return `${dt.getMonth() + 1}/${dt.getDate()}`;
  } catch {
    return d;
  }
}

function titleCase(s: string) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white shadow-sm border border-[#e8d8d2] rounded-lg px-3 py-2 shadow-xl text-xs">
      {label && <p className="text-brand-slate mb-1">{label}</p>}
      {payload.map((entry: any, i: number) => (
        <p key={i} className="font-semibold" style={{ color: entry.color }}>
          {entry.name}:{' '}
          {typeof entry.value === 'number' && entry.value < 1
            ? `$${entry.value.toFixed(3)}`
            : entry.value}
        </p>
      ))}
    </div>
  );
}

function Panel({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass p-6 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-brand-pink">{icon}</span>
        <h2 className="text-brand-navy font-semibold text-sm">{title}</h2>
      </div>
      <p className="text-[11px] text-brand-muted mb-4">{subtitle}</p>
      {children}
    </div>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result: any = await fetch('/api/dashboard/analytics').then((r: any) => r.json());
      if (result.success === false) {
        setError(result.error || 'Failed to load analytics');
        return;
      }
      setData((result.data ?? result) as AnalyticsData);
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <div className="flex items-center gap-3 text-brand-slate">
          <RefreshCw size={20} className="animate-spin" />
          <span>Loading analytics&hellip;</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-transparent p-8">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl font-bold text-brand-navy mb-2">Analytics</h1>
          <div className="mt-8 glass p-8 rounded-lg text-center">
            <AlertCircle size={40} className="mx-auto text-accent-warn mb-3" />
            <p className="text-brand-slate mb-4">{error || 'No data available'}</p>
            <button
              onClick={loadData}
              className="glass-hover px-4 py-2 rounded-lg text-sm text-brand-pink inline-flex items-center gap-2"
            >
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const axisTickStyle = { fill: '#6b7280', fontSize: 11 };

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-brand-navy mb-1">Analytics</h1>
            <p className="text-brand-slate text-sm">Performance insights and trends</p>
          </div>
          <button
            onClick={loadData}
            className="glass-hover px-4 py-2 rounded-lg text-sm text-brand-pink flex items-center gap-2"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Call Volume */}
          <Panel icon={<Activity size={18} />} title="Call Volume" subtitle="Last 30 days">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={data.callVolume}>
                <defs>
                  <linearGradient id="gVol" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" />
                <XAxis dataKey="date" tick={axisTickStyle} tickFormatter={shortDate} />
                <YAxis tick={axisTickStyle} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  name="Calls"
                  stroke="#00d4ff"
                  fill="url(#gVol)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Panel>

          {/* Outcome Distribution */}
          <Panel icon={<BarChart3 size={18} />} title="Outcome Distribution" subtitle="By call result">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.outcomes} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" horizontal={false} />
                <XAxis type="number" tick={axisTickStyle} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="outcome"
                  tick={axisTickStyle}
                  width={120}
                  tickFormatter={titleCase}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                  {data.outcomes.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          {/* Sentiment Breakdown */}
          <Panel icon={<TrendingUp size={18} />} title="Sentiment Breakdown" subtitle="Caller mood analysis">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.sentiments} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" horizontal={false} />
                <XAxis type="number" tick={axisTickStyle} allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="sentiment"
                  tick={axisTickStyle}
                  width={100}
                  tickFormatter={titleCase}
                />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" name="Count" radius={[0, 4, 4, 0]}>
                  {data.sentiments.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={SENTIMENT_COLORS[entry.sentiment.toLowerCase()] || '#6b7280'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          {/* Duration Distribution */}
          <Panel icon={<Clock size={18} />} title="Duration Distribution" subtitle="Call length buckets">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.durations}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" />
                <XAxis dataKey="bucket" tick={axisTickStyle} />
                <YAxis tick={axisTickStyle} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" name="Calls" fill="#7c3aed" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>

          {/* Cost Trend */}
          <Panel icon={<DollarSign size={18} />} title="Cost Trend" subtitle="Daily API spend">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.costTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" />
                <XAxis dataKey="date" tick={axisTickStyle} tickFormatter={shortDate} />
                <YAxis tick={axisTickStyle} tickFormatter={(v) => `$${v.toFixed(2)}`} />
                <Tooltip content={<ChartTooltip />} />
                <Line
                  type="monotone"
                  dataKey="cost"
                  name="Cost"
                  stroke="#e6a817"
                  strokeWidth={2}
                  dot={{ fill: '#e6a817', r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          {/* Quality Distribution */}
          <Panel icon={<Star size={18} />} title="Quality Distribution" subtitle="Score buckets">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.qualityDist}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3050" />
                <XAxis dataKey="bucket" tick={axisTickStyle} />
                <YAxis tick={axisTickStyle} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" name="Calls" fill="#00b37e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </div>
      </div>
    </div>
  );
}

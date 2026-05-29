'use client';
import React, { useEffect, useState } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp, TrendingDown, Zap, DollarSign, PhoneOff, Clock, BarChart3 } from 'lucide-react';
function MetricCard({ label, value, subtext, icon: Icon, delta, deltaPositive, }) {
    return (<div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs text-zinc-500 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-white mt-2">{value}</p>
          {subtext && <p className="text-xs text-zinc-400 mt-1">{subtext}</p>}
        </div>
        <div className="text-zinc-700">{Icon}</div>
      </div>
      {delta !== undefined && (<div className="mt-3 flex items-center gap-1 text-xs">
          {deltaPositive ? (<TrendingUp size={14} className="text-green-500"/>) : (<TrendingDown size={14} className="text-red-500"/>)}
          <span className={deltaPositive ? 'text-green-500' : 'text-red-500'}>
            {deltaPositive ? '+' : ''}{delta}% vs last week
          </span>
        </div>)}
    </div>);
}
export default function OverviewPage() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        async function fetchMetrics() {
            try {
                setLoading(true);
                const response = await fetch('/api/dashboard/overview');
                if (!response.ok)
                    throw new Error('Failed to fetch overview');
                const data = await response.json();
                setMetrics(data);
            }
            catch (err) {
                console.error('Error fetching metrics:', err);
                setError('Failed to load metrics');
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
            }
            finally {
                setLoading(false);
            }
        }
        fetchMetrics();
        // Refresh every 30 seconds
        const interval = setInterval(fetchMetrics, 30000);
        return () => clearInterval(interval);
    }, []);
    if (loading && !metrics) {
        return (<div className="min-h-screen bg-background p-8 flex items-center justify-center">
        <p className="text-text-muted">Loading Command Center...</p>
      </div>);
    }
    if (!metrics)
        return null;
    return (<div className="min-h-screen bg-background p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">Command Center</h1>
          <p className="text-zinc-400 mt-1">Real-time voice AI operations overview</p>
        </div>

        {/* Alerts */}
        {metrics.alerts.length > 0 && (<div className="space-y-2">
            {metrics.alerts.map((alert, idx) => (<div key={idx} className={`flex gap-3 p-3 rounded-lg border ${alert.severity === 'error'
                    ? 'bg-red-950/30 border-red-900/50 text-red-300'
                    : alert.severity === 'warning'
                        ? 'bg-yellow-950/30 border-yellow-900/50 text-yellow-300'
                        : 'bg-blue-950/30 border-blue-900/50 text-blue-300'}`}>
                <AlertCircle size={18} className="flex-shrink-0 mt-0.5"/>
                <p className="text-sm">{alert.message}</p>
              </div>))}
          </div>)}

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard label="Total Calls Today" value={metrics.totalCallsToday} icon={<BarChart3 size={20}/>} delta={metrics.deltaCallsVsLastWeek} deltaPositive={metrics.deltaCallsVsLastWeek > 0}/>
          <MetricCard label="Active Now" value={metrics.activeNow} icon={<Zap size={20} className="text-accent"/>} subtext="● Live connections"/>
          <MetricCard label="Avg Duration" value={metrics.avgDurationToday} icon={<Clock size={20}/>}/>
          <MetricCard label="Quality Score" value={metrics.qualityScoreToday.toFixed(1)} subtext="/10" icon={<BarChart3 size={20} className="text-accent-3"/>} delta={metrics.deltaQualityVsLastWeek * 10} deltaPositive={metrics.deltaQualityVsLastWeek > 0}/>

          <MetricCard label="Cost Today" value={`€${metrics.costToday.toFixed(2)}`} icon={<DollarSign size={20}/>}/>
          <MetricCard label="Resolution Rate" value={`${metrics.resolutionRate}%`} icon={<TrendingUp size={20} className="text-accent-3"/>}/>
          <MetricCard label="Avg Latency" value={`${metrics.avgLatency}ms`} icon={<Clock size={20}/>}/>
          <MetricCard label="Escalated" value={metrics.escalatedToday} icon={<PhoneOff size={20}/>}/>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Call Volume */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-white mb-4">Call Volume (7 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={metrics.callVolume7Days}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46"/>
                <XAxis dataKey="date" stroke="#71717a"/>
                <YAxis stroke="#71717a"/>
                <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '6px' }} labelStyle={{ color: '#fafafa' }}/>
                <Line type="monotone" dataKey="count" stroke="hsl(192, 100%, 50%)" strokeWidth={2} dot={{ fill: 'hsl(192, 100%, 50%)', r: 4 }}/>
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Quality Trend */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
            <h3 className="text-sm font-semibold text-white mb-4">Quality Trend (7 days)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={metrics.qualityTrend7Days}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46"/>
                <XAxis dataKey="date" stroke="#71717a"/>
                <YAxis stroke="#71717a" domain={[6, 10]}/>
                <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '6px' }} labelStyle={{ color: '#fafafa' }}/>
                <Area type="monotone" dataKey="score" fill="hsl(160, 85%, 45%)" stroke="hsl(160, 85%, 45%)" fillOpacity={0.2}/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Calls */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <div className="p-6 border-b border-zinc-800">
            <h3 className="text-sm font-semibold text-white">Recent Calls</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800/50 border-b border-zinc-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Time</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Caller</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Duration</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Quality</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {metrics.recentCalls.map((call) => (<tr key={call.id} className="hover:bg-zinc-800/50 transition-colors cursor-pointer">
                    <td className="px-6 py-3 text-zinc-300">
                      {new Date(call.started_at).toLocaleTimeString('de-DE', {
                hour: '2-digit',
                minute: '2-digit',
            })}
                    </td>
                    <td className="px-6 py-3 text-zinc-300 font-mono text-xs">{call.caller_number}</td>
                    <td className="px-6 py-3 text-zinc-300">
                      {Math.floor(call.duration_seconds / 60)}:{(call.duration_seconds % 60).toString().padStart(2, '0')}
                    </td>
                    <td className="px-6 py-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${call.quality_score >= 8
                ? 'bg-green-950/50 text-green-300'
                : call.quality_score >= 6
                    ? 'bg-yellow-950/50 text-yellow-300'
                    : 'bg-red-950/50 text-red-300'}`}>
                        {call.quality_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-zinc-400 text-xs">{call.outcome}</td>
                  </tr>))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>);
}

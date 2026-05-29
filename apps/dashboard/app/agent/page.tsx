'use client';

import { useState, useEffect } from 'react';
import { Bot, Cpu, Globe, Mic, Wrench, RefreshCw, AlertCircle } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface AgentTool {
  name: string;
  usage_count: number;
}

interface PerformanceEntry {
  outcome: string;
  quality_score: number;
  started_at: string;
}

interface AgentData {
  currentVersion: string;
  model: string;
  voice: string;
  language: string;
  tools: AgentTool[];
  recentPerformance: PerformanceEntry[];
}

export default function AgentConfigPage() {
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgent();
  }, []);

  async function loadAgent() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/dashboard/agent').then((r: any) => r.json());
      const data = res.data ?? (res as unknown as AgentData);
      if (data?.currentVersion) {
        setAgent(data);
      } else {
        setError(res.error || 'Failed to load agent data');
      }
    } catch (e: any) {
      setError(e.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-transparent p-8 flex items-center justify-center">
        <RefreshCw size={24} className="animate-spin text-brand-pink" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="min-h-screen bg-transparent p-8">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl font-bold text-brand-navy mb-2">Agent Configuration</h1>
          <div className="mt-8 p-6 bg-white shadow-sm border border-brand-salmon/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="text-brand-salmon flex-shrink-0" size={20} />
            <p className="text-brand-salmon">{error || 'No agent data available'}</p>
            <button
              onClick={loadAgent}
              className="ml-auto px-4 py-2 bg-brand-cream rounded-lg text-brand-navy text-sm hover:bg-[#dfcdc7] transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const performanceData = agent.recentPerformance.map((p, i) => ({
    call: i + 1,
    score: Math.round(p.quality_score * 100),
    outcome: p.outcome,
  }));

  const totalToolCalls = agent.tools.reduce((sum, t) => sum + t.usage_count, 0);

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-navy mb-2">Agent Configuration</h1>
          <p className="text-brand-slate">Current agent setup, tool usage, and call performance</p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Bot size={16} className="text-brand-pink" />
              <span className="text-brand-slate text-sm">Version</span>
            </div>
            <p className="text-2xl font-bold text-brand-navy">{agent.currentVersion}</p>
          </div>
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Cpu size={16} className="text-brand-pink" />
              <span className="text-brand-slate text-sm">Model</span>
            </div>
            <p className="text-2xl font-bold text-brand-navy">{agent.model}</p>
          </div>
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Mic size={16} className="text-brand-pink" />
              <span className="text-brand-slate text-sm">Voice</span>
            </div>
            <p className="text-2xl font-bold text-brand-navy">{agent.voice}</p>
          </div>
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Globe size={16} className="text-brand-pink" />
              <span className="text-brand-slate text-sm">Language</span>
            </div>
            <p className="text-2xl font-bold text-brand-navy">{agent.language}</p>
          </div>
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-brand-navy flex items-center gap-2">
              <Wrench size={18} className="text-brand-pink" />
              Tool Usage
            </h2>
            <span className="text-brand-slate text-sm">{totalToolCalls} total invocations</span>
          </div>
          {agent.tools.length === 0 ? (
            <p className="text-brand-muted text-sm">No tool usage recorded yet.</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-brand-cream">
                  <th className="text-left text-brand-slate text-sm py-3 font-medium">Tool Name</th>
                  <th className="text-right text-brand-slate text-sm py-3 font-medium">Invocations</th>
                  <th className="text-right text-brand-slate text-sm py-3 font-medium">Share</th>
                </tr>
              </thead>
              <tbody>
                {agent.tools.map((tool) => (
                  <tr key={tool.name} className="border-b border-brand-cream">
                    <td className="py-3 text-brand-navy font-mono text-sm">{tool.name}</td>
                    <td className="py-3 text-right text-brand-pink font-bold">{tool.usage_count}</td>
                    <td className="py-3 text-right text-brand-slate text-sm">
                      {totalToolCalls > 0
                        ? `${Math.round((tool.usage_count / totalToolCalls) * 100)}%`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
          <h2 className="text-lg font-bold text-brand-navy mb-4">Recent Performance</h2>
          {performanceData.length === 0 ? (
            <p className="text-brand-muted text-sm">No performance data recorded yet.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis
                    dataKey="call"
                    stroke="rgba(255,255,255,0.4)"
                    fontSize={12}
                    label={{
                      value: 'Call #',
                      position: 'insideBottom',
                      offset: -5,
                      fill: 'rgba(255,255,255,0.4)',
                    }}
                  />
                  <YAxis
                    stroke="rgba(255,255,255,0.4)"
                    fontSize={12}
                    domain={[0, 100]}
                    label={{
                      value: 'Quality %',
                      angle: -90,
                      position: 'insideLeft',
                      fill: 'rgba(255,255,255,0.4)',
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(24,24,27,0.95)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#a1a1aa' }}
                  />
                  <Bar dataKey="score" fill="#00d4ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>

              <div className="mt-6 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-brand-cream">
                      <th className="text-left text-brand-slate py-2 font-medium">Time</th>
                      <th className="text-left text-brand-slate py-2 font-medium">Outcome</th>
                      <th className="text-right text-brand-slate py-2 font-medium">Quality</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agent.recentPerformance.map((p, i) => (
                      <tr key={i} className="border-b border-brand-cream">
                        <td className="py-2 text-brand-navy">
                          {new Date(p.started_at).toLocaleString()}
                        </td>
                        <td className="py-2">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${
                              p.outcome === 'order'
                                ? 'bg-green-500/20 text-[#16a34a]'
                                : p.outcome === 'reservation'
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : 'bg-[#e8d8d2] text-brand-navy'
                            }`}
                          >
                            {p.outcome}
                          </span>
                        </td>
                        <td className="py-2 text-right font-mono text-brand-navy">
                          {Math.round(p.quality_score * 100)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

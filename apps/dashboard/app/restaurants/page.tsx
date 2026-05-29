'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, Wrench, BarChart3, RefreshCw } from 'lucide-react';

interface OverviewData {
  totalCalls: number;
  activeNow: number;
  avgDuration: number | null;
  todayCalls: number;
}

interface AgentTool {
  name: string;
  usage_count: number;
}

interface AgentData {
  currentVersion: string;
  model: string;
  tools: AgentTool[];
}

export default function RestaurantsPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, agentRes] = await Promise.all([
        fetch('/api/dashboard/overview').then(r => r.json()),
        fetch('/api/dashboard/agent').then(r => r.json()),
      ]);

      const ovData = overviewRes as unknown as OverviewData;
      if (ovData?.totalCalls !== undefined) setOverview(ovData);

      const agData = agentRes.data ?? (agentRes as unknown as AgentData);
      if (agData?.currentVersion) setAgent(agData);
    } catch (e: any) {
      setError(e.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-brand-navy mb-2">Restaurants</h1>
          <p className="text-brand-slate">Restaurant management and multi-tenant configuration</p>
        </div>

        <div className="bg-white shadow-sm border border-brand-peach/30 rounded-lg p-6 mb-8 flex items-start gap-4">
          <AlertTriangle size={24} className="text-yellow-500 flex-shrink-0 mt-0.5" />
          <div>
            <h2 className="text-brand-navy font-bold text-lg mb-1">
              Multi-tenant restaurant system not yet configured
            </h2>
            <p className="text-brand-slate text-sm">
              The multi-restaurant management system is planned but not yet implemented. Currently
              the agent operates as a single-tenant setup for DOBOO Korean SoulFood. Below is a
              summary of all call activity and agent tool usage from the live system.
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw size={24} className="animate-spin text-brand-pink" />
          </div>
        ) : error ? (
          <div className="bg-white shadow-sm border border-brand-salmon/30 rounded-lg p-6">
            <p className="text-brand-salmon">{error}</p>
            <button
              onClick={loadData}
              className="mt-3 px-4 py-2 bg-brand-cream rounded-lg text-brand-navy text-sm hover:bg-[#dfcdc7] transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            {overview && (
              <div className="mb-8">
                <h2 className="text-lg font-bold text-brand-navy mb-4 flex items-center gap-2">
                  <BarChart3 size={18} className="text-brand-pink" />
                  Call Summary
                </h2>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
                    <p className="text-brand-slate text-sm mb-1">Total Calls</p>
                    <p className="text-3xl font-bold text-brand-pink">{overview.totalCalls}</p>
                  </div>
                  <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
                    <p className="text-brand-slate text-sm mb-1">Today</p>
                    <p className="text-3xl font-bold text-brand-navy">{overview.todayCalls ?? '—'}</p>
                  </div>
                  <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
                    <p className="text-brand-slate text-sm mb-1">Active Now</p>
                    <p className="text-3xl font-bold text-[#16a34a]">{overview.activeNow}</p>
                  </div>
                  <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-5">
                    <p className="text-brand-slate text-sm mb-1">Avg Duration</p>
                    <p className="text-3xl font-bold text-brand-navy">
                      {overview.avgDuration ? `${Math.round(overview.avgDuration)}s` : '—'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {agent && (
              <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-6">
                <h2 className="text-lg font-bold text-brand-navy mb-4 flex items-center gap-2">
                  <Wrench size={18} className="text-brand-pink" />
                  Agent Tool Usage
                </h2>
                <p className="text-brand-slate text-sm mb-4">
                  Agent {agent.currentVersion} — Model: {agent.model}
                </p>
                {agent.tools.length === 0 ? (
                  <p className="text-brand-muted text-sm">No tool usage recorded.</p>
                ) : (
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-brand-cream">
                        <th className="text-left text-brand-slate text-sm py-3 font-medium">Tool</th>
                        <th className="text-right text-brand-slate text-sm py-3 font-medium">
                          Usage Count
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {agent.tools.map((t) => (
                        <tr key={t.name} className="border-b border-brand-cream">
                          <td className="py-3 text-brand-navy font-mono text-sm">{t.name}</td>
                          <td className="py-3 text-right text-brand-pink font-bold">
                            {t.usage_count}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

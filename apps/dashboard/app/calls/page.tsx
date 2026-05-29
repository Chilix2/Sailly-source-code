'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Download, Filter, ChevronDown } from 'lucide-react';

interface Call {
  id: string;
  call_sid: string;
  caller_number: string;
  started_at: string;
  duration_seconds: number;
  quality_score: number;
  outcome: string;
  total_cost: number;
  was_escalated: boolean;
  tool_count: number;
}

export default function CallHistoryPage() {
  const router = useRouter();
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [totalCalls, setTotalCalls] = useState(0);
  const [minScore, setMinScore] = useState(0);
  const [maxScore, setMaxScore] = useState(10);
  const [showFilters, setShowFilters] = useState(false);

  const limit = 50;

  const loadCalls = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
        search,
        minScore: minScore.toString(),
        maxScore: maxScore.toString(),
      });
      const response = await fetch(`/api/dashboard/calls?${params}`);
      if (!response.ok) throw new Error('Failed to fetch calls');
      const data = await response.json();
      setCalls(data.calls);
      setTotalCalls(data.total);
    } catch (error) {
      console.error('Error loading calls:', error);
    } finally {
      setLoading(false);
    }
  }, [search, offset, minScore, maxScore, limit]);

  useEffect(() => {
    loadCalls();
  }, [loadCalls]);

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleExport = () => {
    const csv = [
      ['Date', 'Caller', 'Duration', 'Quality', 'Outcome', 'Cost', 'Escalated'],
      ...calls.map((c) => [
        formatTime(c.started_at),
        c.caller_number,
        formatDuration(c.duration_seconds),
        c.quality_score,
        c.outcome,
        c.total_cost,
        c.was_escalated ? 'Yes' : 'No',
      ]),
    ]
      .map((row) => row.map((cell) => `"${cell}"`).join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `calls-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-brand-navy">Call History</h1>
          <p className="text-brand-slate mt-1">Search and filter all calls</p>
        </div>

        {/* Controls */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-4 space-y-4">
          <div className="flex gap-2 flex-col md:flex-row">
            <div className="flex-1 relative">
              <Search size={18} className="absolute left-3 top-3 text-brand-muted" />
              <input
                type="text"
                placeholder="Search by phone or call ID..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setOffset(0);
                }}
                className="w-full pl-10 pr-4 py-2 bg-brand-cream border border-[#e8d8d2] rounded-lg text-brand-navy placeholder-zinc-500 focus:border-accent outline-none transition"
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy transition"
            >
              <Filter size={18} />
              Filters
              <ChevronDown size={16} className={`transition ${showFilters ? 'rotate-180' : ''}`} />
            </button>
            <button
              onClick={handleExport}
              className="flex items-center gap-2 px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy transition"
            >
              <Download size={18} />
              Export CSV
            </button>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-[#e8d8d2]">
              <div>
                <label className="text-xs text-brand-slate mb-2 block">Min Quality</label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.1"
                  value={minScore}
                  onChange={(e) => {
                    setMinScore(parseFloat(e.target.value));
                    setOffset(0);
                  }}
                  className="w-full"
                />
                <div className="text-xs text-brand-slate mt-1">{minScore.toFixed(1)}</div>
              </div>
              <div>
                <label className="text-xs text-brand-slate mb-2 block">Max Quality</label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="0.1"
                  value={maxScore}
                  onChange={(e) => {
                    setMaxScore(parseFloat(e.target.value));
                    setOffset(0);
                  }}
                  className="w-full"
                />
                <div className="text-xs text-brand-slate mt-1">{maxScore.toFixed(1)}</div>
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setMinScore(0);
                    setMaxScore(10);
                    setOffset(0);
                  }}
                  className="w-full px-4 py-2 bg-[#e8d8d2] hover:bg-zinc-600 rounded-lg text-brand-navy text-sm transition"
                >
                  Reset Filters
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Table */}
        {loading ? (
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-8 text-center text-brand-slate">
            Loading calls...
          </div>
        ) : (
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-brand-cream border-b border-brand-cream">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Caller</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Duration</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Quality</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Outcome</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Cost</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Tools</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-brand-slate">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {calls.map((call) => (
                    <tr
                      key={call.id}
                      onClick={() => router.push(`/calls/${call.id}`)}
                      className="hover:bg-[#ecd8d3] transition cursor-pointer"
                    >
                      <td className="px-6 py-3 text-brand-navy text-xs">{formatTime(call.started_at)}</td>
                      <td className="px-6 py-3 text-brand-navy font-mono text-xs">{call.caller_number}</td>
                      <td className="px-6 py-3 text-brand-navy">{formatDuration(call.duration_seconds)}</td>
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
                      <td className="px-6 py-3 text-brand-slate text-xs">{call.outcome}</td>
                      <td className="px-6 py-3 text-brand-slate text-xs">€{call.total_cost.toFixed(2)}</td>
                      <td className="px-6 py-3 text-brand-slate text-xs">{call.tool_count}</td>
                      <td className="px-6 py-3">
                        {call.quality_score < 6 && (
                          <span className="px-2 py-1 bg-[#fff0ee] text-brand-salmon rounded text-xs font-medium">
                            ⚠ Review
                          </span>
                        )}
                        {call.was_escalated && (
                          <span className="px-2 py-1 bg-orange-950/50 text-orange-300 rounded text-xs font-medium">
                            Escalated
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-brand-cream bg-brand-cream">
              <div className="text-xs text-brand-slate">
                Showing {offset + 1} to {Math.min(offset + limit, totalCalls)} of {totalCalls} calls
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] disabled:bg-zinc-900 disabled:text-zinc-600 rounded-lg text-brand-navy text-sm transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= totalCalls}
                  className="px-4 py-2 bg-brand-cream hover:bg-[#dfcdc7] disabled:bg-zinc-900 disabled:text-zinc-600 rounded-lg text-brand-navy text-sm transition"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

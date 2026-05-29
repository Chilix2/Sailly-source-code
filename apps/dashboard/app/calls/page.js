'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Download, Filter, ChevronDown } from 'lucide-react';
export default function CallHistoryPage() {
    const router = useRouter();
    const [calls, setCalls] = useState([]);
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
            if (!response.ok)
                throw new Error('Failed to fetch calls');
            const data = await response.json();
            setCalls(data.calls);
            setTotalCalls(data.total);
        }
        catch (error) {
            console.error('Error loading calls:', error);
        }
        finally {
            setLoading(false);
        }
    }, [search, offset, minScore, maxScore, limit]);
    useEffect(() => {
        loadCalls();
    }, [loadCalls]);
    const formatTime = (isoString) => {
        const date = new Date(isoString);
        return date.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
    };
    const formatDuration = (seconds) => {
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
    return (<div className="min-h-screen bg-background p-6 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white">Call History</h1>
          <p className="text-zinc-400 mt-1">Search and filter all calls</p>
        </div>

        {/* Controls */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-4">
          <div className="flex gap-2 flex-col md:flex-row">
            <div className="flex-1 relative">
              <Search size={18} className="absolute left-3 top-3 text-zinc-500"/>
              <input type="text" placeholder="Search by phone or call ID..." value={search} onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
        }} className="w-full pl-10 pr-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:border-accent outline-none transition"/>
            </div>
            <button onClick={() => setShowFilters(!showFilters)} className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-white transition">
              <Filter size={18}/>
              Filters
              <ChevronDown size={16} className={`transition ${showFilters ? 'rotate-180' : ''}`}/>
            </button>
            <button onClick={handleExport} className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-white transition">
              <Download size={18}/>
              Export CSV
            </button>
          </div>

          {/* Filters */}
          {showFilters && (<div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-zinc-700">
              <div>
                <label className="text-xs text-zinc-400 mb-2 block">Min Quality</label>
                <input type="range" min="0" max="10" step="0.1" value={minScore} onChange={(e) => {
                setMinScore(parseFloat(e.target.value));
                setOffset(0);
            }} className="w-full"/>
                <div className="text-xs text-zinc-400 mt-1">{minScore.toFixed(1)}</div>
              </div>
              <div>
                <label className="text-xs text-zinc-400 mb-2 block">Max Quality</label>
                <input type="range" min="0" max="10" step="0.1" value={maxScore} onChange={(e) => {
                setMaxScore(parseFloat(e.target.value));
                setOffset(0);
            }} className="w-full"/>
                <div className="text-xs text-zinc-400 mt-1">{maxScore.toFixed(1)}</div>
              </div>
              <div className="flex items-end">
                <button onClick={() => {
                setMinScore(0);
                setMaxScore(10);
                setOffset(0);
            }} className="w-full px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-white text-sm transition">
                  Reset Filters
                </button>
              </div>
            </div>)}
        </div>

        {/* Table */}
        {loading ? (<div className="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center text-zinc-400">
            Loading calls...
          </div>) : (<div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-zinc-800/50 border-b border-zinc-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Caller</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Duration</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Quality</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Outcome</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Cost</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Tools</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-zinc-400">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {calls.map((call) => (<tr key={call.id} onClick={() => router.push(`/calls/${call.id}`)} className="hover:bg-zinc-800/50 transition cursor-pointer">
                      <td className="px-6 py-3 text-zinc-300 text-xs">{formatTime(call.started_at)}</td>
                      <td className="px-6 py-3 text-zinc-300 font-mono text-xs">{call.caller_number}</td>
                      <td className="px-6 py-3 text-zinc-300">{formatDuration(call.duration_seconds)}</td>
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
                      <td className="px-6 py-3 text-zinc-400 text-xs">€{call.total_cost.toFixed(2)}</td>
                      <td className="px-6 py-3 text-zinc-400 text-xs">{call.tool_count}</td>
                      <td className="px-6 py-3">
                        {call.quality_score < 6 && (<span className="px-2 py-1 bg-red-950/50 text-red-300 rounded text-xs font-medium">
                            ⚠ Review
                          </span>)}
                        {call.was_escalated && (<span className="px-2 py-1 bg-orange-950/50 text-orange-300 rounded text-xs font-medium">
                            Escalated
                          </span>)}
                      </td>
                    </tr>))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-zinc-800 bg-zinc-800/30">
              <div className="text-xs text-zinc-400">
                Showing {offset + 1} to {Math.min(offset + limit, totalCalls)} of {totalCalls} calls
              </div>
              <div className="flex gap-2">
                <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-900 disabled:text-zinc-600 rounded-lg text-white text-sm transition">
                  Previous
                </button>
                <button onClick={() => setOffset(offset + limit)} disabled={offset + limit >= totalCalls} className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-900 disabled:text-zinc-600 rounded-lg text-white text-sm transition">
                  Next
                </button>
              </div>
            </div>
          </div>)}
      </div>
    </div>);
}

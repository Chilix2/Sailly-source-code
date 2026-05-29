'use client';
import React, { useState, useEffect } from 'react';
import { PipelineVisualizer } from '@/components/PipelineVisualizer';
import { motion } from 'framer-motion';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { fetchAPI } from '@/lib/api';
const mockAggregateMetrics = {
    'twilio-inbound': {
        successRate: 0.995,
        p95Latency: 125,
        errorCount: 1,
    },
    'elevenlabs-connect': {
        successRate: 0.993,
        p95Latency: 280,
        errorCount: 2,
    },
    'claude-proxy': {
        successRate: 0.987,
        p95Latency: 450,
        errorCount: 4,
    },
    'tool-execution': {
        successRate: 0.991,
        p95Latency: 180,
        errorCount: 3,
    },
    'tts-synthesis': {
        successRate: 0.989,
        p95Latency: 320,
        errorCount: 3,
    },
    'confirmation-sent': {
        successRate: 0.994,
        p95Latency: 90,
        errorCount: 1,
    },
    'call-completed': {
        successRate: 0.998,
        p95Latency: 50,
        errorCount: 0,
    },
};
const mockRecentCalls = [
    {
        id: 'conv_abc123',
        callId: 'conv_abc123',
        restaurantId: 'doboo_1',
        timestamp: Date.now() - 120000,
        overallStatus: 'success',
        duration: 2340,
        stages: [
            {
                id: 'twilio-inbound',
                name: 'Twilio Inbound',
                status: 'success',
                latency: 95,
            },
            {
                id: 'elevenlabs-connect',
                name: 'ElevenLabs Connect',
                status: 'success',
                latency: 240,
            },
            {
                id: 'claude-proxy',
                name: 'Claude Proxy / LLM',
                status: 'success',
                latency: 520,
            },
            {
                id: 'tool-execution',
                name: 'Tool Execution',
                status: 'success',
                latency: 180,
            },
            {
                id: 'tts-synthesis',
                name: 'TTS Synthesis',
                status: 'success',
                latency: 280,
            },
            {
                id: 'confirmation-sent',
                name: 'Confirmation Sent',
                status: 'success',
                latency: 85,
            },
            {
                id: 'call-completed',
                name: 'Call Completed',
                status: 'success',
                latency: 0,
            },
        ],
    },
    {
        id: 'conv_def456',
        callId: 'conv_def456',
        restaurantId: 'doboo_1',
        timestamp: Date.now() - 240000,
        overallStatus: 'warning',
        duration: 1890,
        stages: [
            {
                id: 'twilio-inbound',
                name: 'Twilio Inbound',
                status: 'success',
                latency: 110,
            },
            {
                id: 'elevenlabs-connect',
                name: 'ElevenLabs Connect',
                status: 'success',
                latency: 260,
            },
            {
                id: 'claude-proxy',
                name: 'Claude Proxy / LLM',
                status: 'warning',
                latency: 890,
                errorMessage: 'Cache miss - full inference required',
            },
            {
                id: 'tool-execution',
                name: 'Tool Execution',
                status: 'success',
                latency: 150,
            },
            {
                id: 'tts-synthesis',
                name: 'TTS Synthesis',
                status: 'success',
                latency: 310,
            },
            {
                id: 'confirmation-sent',
                name: 'Confirmation Sent',
                status: 'success',
                latency: 72,
            },
            {
                id: 'call-completed',
                name: 'Call Completed',
                status: 'success',
                latency: 0,
            },
        ],
    },
    {
        id: 'conv_ghi789',
        callId: 'conv_ghi789',
        restaurantId: 'doboo_1',
        timestamp: Date.now() - 360000,
        overallStatus: 'error',
        duration: 0,
        stages: [
            {
                id: 'twilio-inbound',
                name: 'Twilio Inbound',
                status: 'success',
                latency: 115,
            },
            {
                id: 'elevenlabs-connect',
                name: 'ElevenLabs Connect',
                status: 'error',
                latency: 0,
                errorMessage: 'WebSocket connection timeout',
            },
            {
                id: 'claude-proxy',
                name: 'Claude Proxy / LLM',
                status: 'error',
            },
            {
                id: 'tool-execution',
                name: 'Tool Execution',
                status: 'error',
            },
            {
                id: 'tts-synthesis',
                name: 'TTS Synthesis',
                status: 'error',
            },
            {
                id: 'confirmation-sent',
                name: 'Confirmation Sent',
                status: 'error',
            },
            {
                id: 'call-completed',
                name: 'Call Completed',
                status: 'error',
            },
        ],
    },
];
export default function PipelinePage() {
    const [selectedCall, setSelectedCall] = useState(null);
    const [stats, setStats] = useState(null);
    const [statsLive, setStatsLive] = useState(false);
    const [statsLoading, setStatsLoading] = useState(true);
    useEffect(() => {
        async function loadStats() {
            setStatsLoading(true);
            const result = await fetchAPI('/api/dashboard/stats');
            if (result.success && result.data) {
                setStats(result.data);
                setStatsLive(true);
            }
            else {
                setStatsLive(false);
            }
            setStatsLoading(false);
        }
        loadStats();
        const interval = setInterval(loadStats, 60000);
        return () => clearInterval(interval);
    }, []);
    return (<div className="min-h-screen bg-background p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text mb-2">
              Call Pipeline <span className="text-accent">Visualizer</span>
            </h1>
            <p className="text-text-dim flex items-center gap-2">
              {statsLive ? (<><Wifi size={14} className="text-accent-3"/> Live data from database</>) : (<><WifiOff size={14} className="text-accent-warn"/> Showing demo data (backend not connected)</>)}
            </p>
          </div>
          {statsLoading && <RefreshCw size={18} className="animate-spin text-accent"/>}
        </div>

        {/* Live stats from DB */}
        {stats && (<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="grid grid-cols-4 gap-4 mb-8">
            <div className="glass p-6 rounded-lg">
              <p className="text-xs text-text-muted mb-1">Today</p>
              <p className="text-3xl font-bold text-accent">{stats.today.total}</p>
              <p className="text-sm text-text-dim mt-1">
                {stats.today.completed} completed &middot; {stats.today.failed} failed
              </p>
            </div>
            <div className="glass p-6 rounded-lg">
              <p className="text-xs text-text-muted mb-1">This Week</p>
              <p className="text-3xl font-bold text-accent">{stats.week.total}</p>
              <p className="text-sm text-text-dim mt-1">
                {stats.week.completed} completed &middot; {stats.week.failed} failed
              </p>
            </div>
            <div className="glass p-6 rounded-lg">
              <p className="text-xs text-text-muted mb-1">All Time</p>
              <p className="text-3xl font-bold text-accent">{stats.allTime.total}</p>
              <p className="text-sm text-text-dim mt-1">
                {stats.allTime.completed} completed &middot; {stats.allTime.failed} failed
              </p>
            </div>
            <div className="glass p-6 rounded-lg">
              <p className="text-xs text-text-muted mb-1">Avg Duration</p>
              <p className="text-3xl font-bold text-accent">
                {stats.allTime.avgDuration ? `${Math.round(stats.allTime.avgDuration)}s` : 'N/A'}
              </p>
              <p className="text-sm text-text-dim mt-1">
                Success rate: {stats.allTime.total > 0
                ? `${Math.round((stats.allTime.completed / stats.allTime.total) * 100)}%`
                : 'N/A'}
              </p>
            </div>
          </motion.div>)}

        {/* Aggregate view */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-12 glass p-8 rounded-lg">
          <PipelineVisualizer aggregateMetrics={mockAggregateMetrics} isAggregate={true}/>
        </motion.div>

        {/* Recent calls */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <h2 className="text-lg font-bold text-text mb-4">Recent Calls</h2>
          <div className="space-y-4">
            {mockRecentCalls.map((call, index) => (<motion.div key={call.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 + index * 0.1 }} onClick={() => setSelectedCall(selectedCall?.id === call.id ? null : call)} className="glass-hover p-6 rounded-lg cursor-pointer">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-text">{call.id}</h3>
                    <p className="text-sm text-text-muted mt-1">
                      Restaurant: {call.restaurantId} · Duration: {(call.duration / 1000).toFixed(1)}s
                    </p>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-semibold ${call.overallStatus === 'success'
                ? 'bg-accent-3/20 text-accent-3'
                : call.overallStatus === 'warning'
                    ? 'bg-accent-warn/20 text-accent-warn'
                    : 'bg-accent-danger/20 text-accent-danger'}`}>
                    {call.overallStatus.toUpperCase()}
                  </div>
                </div>
              </motion.div>))}
          </div>
        </motion.div>

        {/* Selected call detail */}
        {selectedCall && (<motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mt-12 glass p-8 rounded-lg">
            <PipelineVisualizer event={selectedCall}/>
          </motion.div>)}
      </motion.div>
    </div>);
}

'use client';
import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Download, Trash2, Flag, MessageSquare, BarChart3, Zap } from 'lucide-react';
import { AudioPlayerProvider, AudioPlayerButton, AudioPlayerProgress, AudioPlayerTime, AudioPlayerDuration, AudioPlayerSpeed } from '@/components/ui/audio-player';
import { Waveform } from '@/components/ui/waveform';
function QualityBar({ label, score }) {
    return (<div className="space-y-1">
      <div className="flex justify-between items-center text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="text-zinc-300 font-mono">{score.toFixed(1)}/10</span>
      </div>
      <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div className={`h-full transition-all ${score >= 8 ? 'bg-green-500' : score >= 6 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${(score / 10) * 100}%` }}/>
      </div>
    </div>);
}
export default function CallDetailPage() {
    const params = useParams();
    const router = useRouter();
    const callId = params.id;
    const [detail, setDetail] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [waveformData] = useState(Array(50).fill(0).map(() => Math.random()));
    const [currentTime, setCurrentTime] = useState(0);
    const [showConfirmDelete, setShowConfirmDelete] = useState(false);
    useEffect(() => {
        async function fetchDetail() {
            try {
                setLoading(true);
                const response = await fetch(`/api/dashboard/calls/${callId}`);
                if (!response.ok)
                    throw new Error('Failed to fetch call details');
                const data = await response.json();
                setDetail(data);
            }
            catch (err) {
                console.error('Error fetching call detail:', err);
                setError('Failed to load call details');
            }
            finally {
                setLoading(false);
            }
        }
        if (callId)
            fetchDetail();
    }, [callId]);
    if (loading) {
        return <div className="min-h-screen bg-background p-8 flex items-center justify-center"><p className="text-zinc-400">Loading call...</p></div>;
    }
    if (error || !detail) {
        return <div className="min-h-screen bg-background p-8"><p className="text-red-400">{error}</p></div>;
    }
    const call = detail.call;
    const startTime = new Date(call.started_at);
    const duration = call.duration_seconds;
    return (<div className="min-h-screen bg-background p-6 md:p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-white font-mono">{call.call_sid}</h1>
              <span className={`px-2 py-1 rounded text-xs font-medium ${call.quality_score >= 8 ? 'bg-green-950/50 text-green-300' :
            call.quality_score >= 6 ? 'bg-yellow-950/50 text-yellow-300' :
                'bg-red-950/50 text-red-300'}`}>{call.quality_score.toFixed(1)}/10</span>
            </div>
            <p className="text-zinc-400 text-sm">
              {startTime.toLocaleString('de-DE')} · {Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')} · {call.outcome}
            </p>
          </div>
          <div className="flex gap-2">
            <button className="p-2 hover:bg-zinc-800 rounded-lg transition"><Flag size={20}/></button>
            <button className="p-2 hover:bg-zinc-800 rounded-lg transition"><Download size={20}/></button>
            <button onClick={() => setShowConfirmDelete(true)} className="p-2 hover:bg-red-950/50 rounded-lg transition text-red-400">
              <Trash2 size={20}/>
            </button>
          </div>
        </div>

        {/* Audio Player */}
        <AudioPlayerProvider>
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
            <div className="flex items-center gap-4">
              <AudioPlayerButton />
              <AudioPlayerProgress />
              <div className="flex items-center gap-1 text-sm">
                <AudioPlayerTime /> / <AudioPlayerDuration />
              </div>
              <AudioPlayerSpeed />
            </div>
            
            {/* Waveform */}
            <Waveform data={waveformData} height={60} barColor="hsl(192, 100%, 50%)"/>

            {/* Download options */}
            <div className="flex gap-2 text-xs">
              <button className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded transition">
                <Download size={14} className="inline mr-1"/>
                Caller Audio
              </button>
              <button className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 rounded transition">
                <Download size={14} className="inline mr-1"/>
                Agent Audio
              </button>
            </div>
          </div>
        </AudioPlayerProvider>

        {/* Transcript */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <MessageSquare size={18}/>
            Transcript
          </h3>
          <div className="bg-zinc-800/50 p-4 rounded-lg font-mono text-sm space-y-3 max-h-96 overflow-y-auto">
            {detail.transcript.map((turn) => (<div key={turn.id} className="space-y-1">
                <div className="flex gap-2">
                  <span className={`text-xs font-mono ${turn.speaker === 'caller' ? 'text-accent-warn' : 'text-accent-3'}`}>
                    [{turn.speaker.toUpperCase()}]
                  </span>
                  <span className="text-xs text-zinc-500">{(turn.timestamp_ms / 1000).toFixed(1)}s</span>
                </div>
                <p className="text-zinc-200">{turn.content}</p>
              </div>))}
          </div>
        </div>

        {/* Tool Calls */}
        {detail.tools.length > 0 && (<div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Zap size={18}/>
              Tool Calls ({detail.tools.length})
            </h3>
            <div className="space-y-3">
              {detail.tools.map((tool) => (<div key={tool.id} className="bg-zinc-800/50 p-4 rounded-lg space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-accent">{tool.tool_name}</span>
                    <span className={`text-xs ${tool.success ? 'text-green-400' : 'text-red-400'}`}>
                      {tool.success ? '✓ Success' : '✗ Failed'} · {tool.duration_ms}ms
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400">
                    <div>
                      <p>Input:</p>
                      <pre className="bg-zinc-900 p-2 rounded overflow-x-auto">
                        {JSON.stringify(tool.input_params, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <p>Output:</p>
                      <pre className="bg-zinc-900 p-2 rounded overflow-x-auto">
                        {JSON.stringify(tool.output_result, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>))}
            </div>
          </div>)}

        {/* Quality Evaluation */}
        {detail.quality && (<div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-6">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <BarChart3 size={18}/>
              Quality Evaluation
            </h3>

            {/* Scores Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <QualityBar label="Greeting" score={detail.quality.greeting_score}/>
              <QualityBar label="Compliance" score={detail.quality.instruction_compliance_score}/>
              <QualityBar label="Emotion" score={detail.quality.emotional_handling_score}/>
              <QualityBar label="Resolution" score={detail.quality.problem_resolution_score}/>
              <QualityBar label="Fluency" score={detail.quality.german_fluency_score}/>
              <QualityBar label="Tools" score={detail.quality.tool_usage_score}/>
              <QualityBar label="Closure" score={detail.quality.closure_score}/>
            </div>

            {/* Summary */}
            <div className="space-y-2">
              <p className="text-xs text-zinc-400">Summary</p>
              <p className="text-sm text-zinc-200">{detail.quality.summary}</p>
            </div>

            {/* Issues */}
            {detail.quality.issues_detected.length > 0 && (<div className="space-y-2">
                <p className="text-xs text-zinc-400">Issues Detected</p>
                <ul className="space-y-1">
                  {detail.quality.issues_detected.map((issue, idx) => (<li key={idx} className="text-sm text-red-300 flex gap-2">
                      <span>•</span>
                      <span>{issue}</span>
                    </li>))}
                </ul>
              </div>)}
          </div>)}

        {/* Metadata */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
          <h3 className="text-sm font-semibold text-white">Metadata</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-zinc-500 text-xs">Call ID</p>
              <p className="text-zinc-200 font-mono text-xs mt-1">{call.id.slice(0, 12)}...</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Caller</p>
              <p className="text-zinc-200 font-mono text-xs mt-1">{call.caller_number}</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Language</p>
              <p className="text-zinc-200 text-xs mt-1">{call.language}</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Sentiment</p>
              <p className="text-zinc-200 text-xs mt-1">{call.sentiment || '—'}</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Total Tokens</p>
              <p className="text-zinc-200 font-mono text-xs mt-1">
                {(call.total_input_tokens + call.total_output_tokens).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Cost</p>
              <p className="text-zinc-200 text-xs mt-1">
                €{(call.total_cost_tokens + call.total_cost_telephony).toFixed(3)}
              </p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Avg Latency</p>
              <p className="text-zinc-200 text-xs mt-1">{call.avg_latency_ms}ms</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">P95 Latency</p>
              <p className="text-zinc-200 text-xs mt-1">{call.p95_latency_ms}ms</p>
            </div>
          </div>
        </div>

        {/* Delete Confirmation Modal */}
        {showConfirmDelete && (<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 max-w-sm space-y-4">
              <h2 className="text-lg font-bold text-white">Delete Call Data</h2>
              <p className="text-sm text-zinc-300">
                This will permanently delete the audio, transcript, and all associated data for this call. This action cannot be undone.
              </p>
              <div className="flex gap-2">
                <button onClick={() => setShowConfirmDelete(false)} className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-white transition">
                  Cancel
                </button>
                <button onClick={() => {
                // TODO: Call delete API
                setShowConfirmDelete(false);
                router.push('/calls');
            }} className="flex-1 px-4 py-2 bg-red-900 hover:bg-red-800 rounded-lg text-white transition">
                  Delete
                </button>
              </div>
            </div>
          </div>)}
      </div>
    </div>);
}

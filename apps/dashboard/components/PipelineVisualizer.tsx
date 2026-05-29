'use client';

import React, { useState } from 'react';
import { AlertCircle, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

interface PipelineStage {
  id: string;
  name: string;
  status: 'success' | 'warning' | 'error' | 'loading';
  latency?: number;
  errorMessage?: string;
  details?: string;
}

interface PipelineEvent {
  id: string;
  callId: string;
  stages: PipelineStage[];
  timestamp: number;
}

interface PipelineVisualizerProps {
  event?: PipelineEvent;
  aggregateMetrics?: {
    [key: string]: {
      successRate: number;
      p95Latency: number;
      errorCount: number;
    };
  };
  isAggregate?: boolean;
}

const PIPELINE_STAGES = [
  {
    id: 'twilio-inbound',
    name: 'Twilio Inbound',
    color: 'from-blue-500 to-blue-600',
    icon: '📞',
  },
  {
    id: 'elevenlabs-connect',
    name: 'ElevenLabs Connect',
    color: 'from-purple-500 to-purple-600',
    icon: '🎙️',
  },
  {
    id: 'claude-proxy',
    name: 'Claude Proxy / LLM',
    color: 'from-pink-500 to-pink-600',
    icon: '🧠',
  },
  {
    id: 'tool-execution',
    name: 'Tool Execution',
    color: 'from-orange-500 to-orange-600',
    icon: '⚙️',
  },
  {
    id: 'tts-synthesis',
    name: 'TTS Synthesis',
    color: 'from-green-500 to-green-600',
    icon: '🔊',
  },
  {
    id: 'confirmation-sent',
    name: 'Confirmation Sent',
    color: 'from-cyan-500 to-cyan-600',
    icon: '✓',
  },
  {
    id: 'call-completed',
    name: 'Call Completed',
    color: 'from-teal-500 to-teal-600',
    icon: '✨',
  },
];

function getStatusColor(status: string): string {
  switch (status) {
    case 'success':
      return 'bg-accent-3 shadow-lg shadow-accent-3/30';
    case 'warning':
      return 'bg-accent-warn shadow-lg shadow-accent-warn/30';
    case 'error':
      return 'bg-accent-danger shadow-lg shadow-accent-danger/30 animate-pulse';
    case 'loading':
      return 'bg-brand-pink opacity-60 animate-pulse';
    default:
      return 'bg-text-muted';
  }
}

export function PipelineVisualizer({ event, aggregateMetrics, isAggregate }: PipelineVisualizerProps) {
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  if (isAggregate && aggregateMetrics) {
    return (
      <div className="w-full">
        <h2 className="text-lg font-bold text-text mb-6 flex items-center gap-2">
          <Zap size={20} className="text-brand-pink" />
          System Pipeline Health
        </h2>

        <div className="flex gap-2 overflow-x-auto pb-4">
          {PIPELINE_STAGES.map((stage) => {
            const metrics = aggregateMetrics[stage.id];
            const successRate = metrics?.successRate || 0;
            const p95Latency = metrics?.p95Latency || 0;

            return (
              <motion.button
                key={stage.id}
                onClick={() => setExpandedStage(expandedStage === stage.id ? null : stage.id)}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ scale: 1.05 }}
                className="glass-hover p-4 min-w-max rounded-lg cursor-pointer flex flex-col items-center gap-3"
              >
                <div className={`w-4 h-4 rounded-full ${getStatusColor(successRate >= 0.99 ? 'success' : successRate >= 0.95 ? 'warning' : 'error')}`} />
                <div className="text-center">
                  <p className="text-sm font-semibold text-text">{stage.name}</p>
                  <p className="text-xs text-text-muted mt-1">{(successRate * 100).toFixed(1)}% success</p>
                  <p className="text-xs text-text-dim">{p95Latency}ms p95</p>
                </div>
              </motion.button>
            );
          })}
        </div>

        {expandedStage && aggregateMetrics[expandedStage] && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6 glass p-6 rounded-lg"
          >
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-text-muted mb-1">Success Rate</p>
                <p className="text-2xl font-bold text-brand-pink">
                  {(aggregateMetrics[expandedStage].successRate * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted mb-1">P95 Latency</p>
                <p className="text-2xl font-bold text-brand-pink">
                  {aggregateMetrics[expandedStage].p95Latency}ms
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted mb-1">Errors (1h)</p>
                <p className="text-2xl font-bold text-accent-danger">
                  {aggregateMetrics[expandedStage].errorCount}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    );
  }

  if (event) {
    return (
      <div className="w-full">
        <h2 className="text-lg font-bold text-text mb-6">Call Pipeline: {event.callId}</h2>

        <div className="flex gap-0 items-stretch overflow-x-auto pb-4">
          {event.stages.map((stage, i) => (
            <React.Fragment key={stage.id}>
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className="flex flex-col items-center"
              >
                <div
                  className={`w-20 h-20 rounded-lg glass flex flex-col items-center justify-center cursor-pointer transition-all ${getStatusColor(
                    stage.status
                  )}`}
                  onClick={() => setExpandedStage(expandedStage === stage.id ? null : stage.id)}
                >
                  <div className="text-center">
                    <p className="text-xs font-semibold text-brand-navy">{stage.latency || 0}ms</p>
                    {stage.status === 'error' && <AlertCircle size={16} className="mx-auto mt-1" />}
                  </div>
                </div>
                <p className="text-xs text-text-muted mt-2 text-center w-20">{stage.name}</p>
              </motion.div>

              {i < event.stages.length - 1 && (
                <div className="flex items-center px-2">
                  <div className="h-1 w-4 bg-border rounded" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>

        {expandedStage &&
          event.stages.find((s) => s.id === expandedStage) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-6 glass p-6 rounded-lg"
            >
              {event.stages
                .filter((s) => s.id === expandedStage)
                .map((stage) => (
                  <div key={stage.id}>
                    <h3 className="text-sm font-bold text-brand-pink mb-3">{stage.name}</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-text-muted">Status:</span>
                        <span className={getStatusColor(stage.status).split(' ')[0]}>
                          {stage.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-muted">Latency:</span>
                        <span className="text-brand-pink font-mono">{stage.latency}ms</span>
                      </div>
                      {stage.errorMessage && (
                        <div className="mt-3 p-2 bg-accent-danger/10 border border-accent-danger/30 rounded text-sm text-accent-danger">
                          {stage.errorMessage}
                        </div>
                      )}
                      {stage.details && (
                        <div className="mt-3 p-2 bg-accent/10 border border-accent/30 rounded text-sm text-accent-2 font-mono text-xs">
                          {stage.details}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </motion.div>
          )}
      </div>
    );
  }

  return (
    <div className="text-center py-12">
      <AlertCircle size={32} className="mx-auto text-text-muted mb-3" />
      <p className="text-text-muted">No pipeline data available</p>
    </div>
  );
}

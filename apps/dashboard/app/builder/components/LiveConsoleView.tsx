'use client';

import React, { useEffect, useState } from 'react';
import { useActiveCalls, useLiveTrace } from '@/lib/api/debugger-client';
import { LiveEvent } from '@/types/sailly-debugger';
import { useDebuggerStore } from '@/lib/store/debugger-store';

/**
 * Phase 6: Live Console
 * Polls active calls and live trace events in real-time
 * Shows streaming transcript, event stream, and latency panes
 */
export function LiveConsoleView() {
  const { data: activeCallsData } = useActiveCalls();
  const [selectedCallSid, setSelectedCallSid] = useState<string | null>(null);
  const selectedTenantId = useDebuggerStore((state) => state.selectedTenantId);
  const { data: liveTraceData } = useLiveTrace(
    selectedCallSid || '',
    selectedTenantId || undefined
  );

  const [events, setEvents] = useState<LiveEvent[]>([]);

  // Update events when live trace changes
  useEffect(() => {
    if (liveTraceData?.events) {
      setEvents(liveTraceData.events);
    }
  }, [liveTraceData]);

  // Auto-scroll to latest event
  const eventListRef = React.useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (eventListRef.current) {
      eventListRef.current.scrollTop = eventListRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b border-brand-cream bg-slate-50 p-4 flex-shrink-0">
        <h2 className="text-sm font-semibold text-brand-navy mb-3">Live Console</h2>

        {/* Active calls selector */}
        <div>
          <label className="block text-xs text-brand-muted mb-1">Select Call</label>
          <select
            value={selectedCallSid || ''}
            onChange={(e) => setSelectedCallSid(e.target.value || null)}
            className="w-full px-2 py-1 bg-slate-50 border border-brand-cream rounded text-sm text-brand-navy focus:outline-none focus:border-blue-500"
          >
            <option value="">-- Choose an active call --</option>
            {activeCallsData?.calls?.map((call) => (
              <option key={call.call_sid} value={call.call_sid}>
                {call.call_sid.substring(0, 8)}... • {call.tenant_id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!selectedCallSid ? (
        <div className="flex-1 flex items-center justify-center text-brand-muted text-sm">
          {activeCallsData?.calls?.length === 0
            ? 'No active calls available'
            : 'Select a call to view live console'}
        </div>
      ) : (
        <div className="flex-1 overflow-hidden flex flex-col gap-4 p-4">
          {/* Transcript pane */}
          <div className="flex-1 bg-slate-50 rounded border border-brand-cream overflow-hidden flex flex-col">
            <div className="border-b border-brand-cream bg-slate-50 px-3 py-2 text-xs font-semibold text-brand-navy flex-shrink-0">
              Transcript
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs">
              {events
                .filter((e) => e.type === 'transcript')
                .map((e, idx) => (
                  <div key={idx} className="text-slate-700">
                    <span className="text-slate-500">
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </span>
                    {' • '}
                    <span
                      className={
                        e.data?.role === 'user' ? 'text-blue-700' : 'text-green-700'
                      }
                    >
                      {e.data?.role || 'unknown'}:
                    </span>{' '}
                    {e.data?.text || e.message}
                  </div>
                ))}
            </div>
          </div>

          {/* Event stream pane */}
          <div className="flex-1 bg-slate-50 rounded border border-brand-cream overflow-hidden flex flex-col">
            <div className="border-b border-brand-cream bg-slate-50 px-3 py-2 text-xs font-semibold text-brand-navy flex-shrink-0">
              Event Stream
            </div>
            <div
              ref={eventListRef}
              className="flex-1 overflow-y-auto p-3 space-y-1 font-mono text-xs"
            >
              {events.map((e, idx) => (
                <div
                  key={idx}
                  className={`text-xs ${
                    e.type === 'error' ? 'text-red-600' : 'text-brand-muted'
                  }`}
                >
                  <span className="text-slate-600">
                    {new Date(e.timestamp).toLocaleTimeString()}
                  </span>
                  {' '} {e.type} {' '}
                  <span className="text-slate-500">{e.message}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Latency pane */}
          <div className="bg-slate-50 rounded border border-brand-cream p-3">
            <div className="text-xs font-semibold text-brand-navy mb-2">Latencies</div>
            <div className="grid grid-cols-4 gap-2 text-xs">
              {[
                { label: 'Last Turn', key: 'last_turn_ms' },
                { label: 'Avg Turn', key: 'avg_turn_ms' },
                { label: 'LLM', key: 'llm_ms' },
                { label: 'TTS', key: 'tts_ms' },
              ].map((stat) => (
                <div key={stat.key} className="bg-white border border-brand-cream px-2 py-1 rounded-lg">
                  <div className="text-brand-muted">{stat.label}</div>
                  <div className="text-lg font-semibold text-brand-navy">
                    {liveTraceData?.events?.[0]?.data?.[stat.key] || '—'}ms
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

'use client';

import React from 'react';
import { useMonitorCalls } from '@/lib/api/debugger-client';
import { MOCK_SESSIONS } from '@/lib/api/mock-data';
import { useDebuggerStore } from '@/lib/store/debugger-store';

import { DebuggerHeader } from './components/DebuggerHeader';
import { SessionList } from './components/SessionList';
import { MainContent } from './components/MainContent';
import { TurnStrip } from './components/TurnStrip';
import { ScenarioDetailsPanel } from './components/ScenarioDetailsPanel';
import { LayerSelector } from './components/LayerSelector';
import { InspectedDetailPanel } from './components/InspectedDetailPanel';

export default function DebuggerPage() {
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK === 'true';
  const { selectedTenantId, selectedCallSid } = useDebuggerStore();

  // Use mock data if enabled, otherwise use API
  const { data: callsData, isLoading } = useMock
    ? { data: { calls: MOCK_SESSIONS, count: MOCK_SESSIONS.length }, isLoading: false }
    : useMonitorCalls(selectedTenantId, { limit: 100 });

  // Find selected call for scenario info
  const selectedCall = selectedCallSid
    ? callsData?.calls.find((c) => c.call_sid === selectedCallSid)
    : null;

  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-900">
      <DebuggerHeader />

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {/* Main 3-pane layout: layers (left) | flow (center) | code/config (right) */}
        <div className="flex min-h-0 flex-1 overflow-hidden gap-0">
          {/* Left rail: call selector + layer selector + compact scenario */}
          <div className="flex w-80 flex-col overflow-hidden border-r border-brand-cream bg-[#fdf5f2]">
            <SessionList sessions={callsData?.calls || []} loading={isLoading} />
            {selectedCallSid ? (
              <div className="flex-1 overflow-y-auto">
                <LayerSelector />
                <div className="border-t border-brand-cream p-4">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-muted">
                    Call Scenario
                  </h3>
                  {selectedCall?.scenario_tags ? (
                    <ScenarioDetailsPanel scenario={selectedCall.scenario_tags} />
                  ) : (
                    <div className="text-xs italic text-brand-muted">
                      Scenario classification pending (check back after the call
                      finishes)
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 p-4 text-xs italic text-brand-muted">
                Select a call to inspect Layer 1/2/3 per turn.
              </div>
            )}
          </div>

          {/* Center: flowchart / analytical views */}
          <div className="flex flex-1 flex-col overflow-hidden">
            {selectedCallSid ? (
              <MainContent callSid={selectedCallSid} />
            ) : (
              <div className="flex flex-1 items-center justify-center text-brand-muted">
                Select a call from the call selector to begin debugging
              </div>
            )}
          </div>

          {/* Right rail: inspected field (Pretty + Raw) */}
          <div className="flex w-96 flex-col overflow-hidden border-l border-brand-cream bg-white">
            {selectedCallSid ? (
              <InspectedDetailPanel callSid={selectedCallSid} />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-brand-muted">
                No call selected
              </div>
            )}
          </div>
        </div>

        {/* Full-width turn strip */}
        <div className="h-28 border-t border-brand-cream bg-white">
          {selectedCallSid ? (
            <TurnStrip callSid={selectedCallSid} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-brand-muted">
              Select a call to browse turns
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useMemo, useState } from 'react';
import { SessionRow } from '@/types/sailly-debugger';
import { useDebuggerStore } from '@/lib/store/debugger-store';
import { ChevronDown, Search } from 'lucide-react';

export function SessionList({
  sessions,
  loading,
}: {
  sessions: SessionRow[];
  loading: boolean;
}) {
  const { selectedCallSid, setSelectedCallSid, searchQuery, setSearchQuery } =
    useDebuggerStore();
  const [open, setOpen] = useState(false);

  const filteredSessions = useMemo(() => {
    if (!searchQuery) return sessions;
    return sessions.filter((s) =>
      s.call_sid.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [sessions, searchQuery]);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.call_sid === selectedCallSid),
    [sessions, selectedCallSid],
  );

  return (
    <div className="relative flex-shrink-0 border-b border-[#e8d8d2] bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
            Selected Call
          </div>
          <div className="mt-0.5 text-xs text-brand-muted">
            Search and switch calls
          </div>
        </div>
        {selectedSession?.scenario_tags && (
          <span className="rounded-full border border-brand-peach bg-brand-peach/20 px-2 py-0.5 text-[10px] font-semibold text-brand-navy">
            {selectedSession.scenario_tags.primary_scenario.split('_').join(' ')} ·{' '}
            {selectedSession.scenario_tags.scenario_phase}
          </span>
        )}
      </div>

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="mb-2 flex w-full items-center justify-between rounded-xl border border-[#e8d8d2] bg-[#fdf5f2] px-3 py-2 text-left shadow-sm transition hover:border-brand-pink/50"
      >
        <span className="min-w-0">
          <span className="block truncate font-mono text-xs font-semibold text-brand-navy">
            {selectedSession ? selectedSession.call_sid.slice(-18) : 'Choose a call'}
          </span>
          <span className="mt-0.5 block text-[10px] text-brand-muted">
            {selectedSession
              ? `${Math.floor(selectedSession.duration_seconds / 60)}m ${
                  selectedSession.duration_seconds % 60
                }s · ${selectedSession.turn_count} turns`
              : 'No call selected'}
          </span>
        </span>
        <ChevronDown
          className={`h-4 w-4 flex-shrink-0 text-brand-muted transition ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      <div className="relative">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-brand-muted" />
        <input
          type="text"
          placeholder="Search call SID..."
          value={searchQuery}
          onFocus={() => setOpen(true)}
          onChange={(event) => {
            setSearchQuery(event.target.value);
            setOpen(true);
          }}
          className="w-full rounded-xl border border-[#e8d8d2] bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder-brand-muted focus:outline-none focus:ring-2 focus:ring-brand-pink/30"
        />
      </div>

      {open && (
        <div className="absolute left-4 right-4 top-[132px] z-30 max-h-80 overflow-y-auto rounded-xl border border-[#e8d8d2] bg-white shadow-xl">
          {loading ? (
            <div className="p-4 text-center text-sm text-brand-muted">
              Loading calls...
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="p-4 text-center text-sm text-brand-muted">
              No calls found
            </div>
          ) : (
            <div className="divide-y divide-[#f5e9e4]">
              {filteredSessions.map((session) => (
              <button
                key={session.call_sid}
                type="button"
                onClick={() => {
                  setSelectedCallSid(session.call_sid);
                  setOpen(false);
                }}
                className={`w-full text-left px-3 py-3 transition flex items-start justify-between ${
                  selectedCallSid === session.call_sid
                    ? 'bg-brand-pink/10 text-brand-navy border-l-4 border-l-brand-pink'
                    : 'bg-white text-slate-900 hover:bg-[#fdf5f2]'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-mono text-xs truncate text-brand-navy font-semibold">
                      {session.call_sid.slice(-12)}
                    </div>
                    {/* Scenario badge */}
                    {session.scenario_tags && (
                      <div className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 bg-brand-peach/20 border border-brand-peach rounded text-xs font-semibold text-brand-navy whitespace-nowrap">
                        <span>{session.scenario_tags.primary_scenario.split('_').join(' ')}</span>
                        <span className="text-brand-pink">·</span>
                        <span>{session.scenario_tags.scenario_phase}</span>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-brand-muted mt-1 flex gap-2 flex-wrap">
                    <span>
                      {Math.floor(session.duration_seconds / 60)}m{' '}
                      {session.duration_seconds % 60}s
                    </span>
                    <span>•</span>
                    <span>{session.turn_count} turns</span>
                  </div>
                  {session.ended_properly ? (
                    <span className="text-xs text-brand-salmon mt-1">✓ Ended</span>
                  ) : (
                    <span className="text-xs text-red-500 mt-1">✗ Incomplete</span>
                  )}
                  {/* Modifiers tags */}
                  {session.scenario_tags?.modifiers && session.scenario_tags.modifiers.length > 0 && (
                    <div className="text-xs text-brand-muted mt-1 flex gap-1 flex-wrap">
                      {session.scenario_tags.modifiers.map((mod) => (
                        <span key={mod} className="px-1.5 py-0.5 bg-slate-100 rounded text-xs">
                          {mod}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

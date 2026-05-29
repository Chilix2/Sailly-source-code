import { useQuery } from '@tanstack/react-query';
import {
  SessionRow,
  TurnRow,
  LiveEvent,
  Layer1Decision,
} from '@/types/sailly-debugger';

// Empty API_BASE means use relative URLs through nginx proxy
const API_BASE = process.env.NEXT_PUBLIC_SAILLY_API_BASE || '';

// ────────────────────────────────────────────────────────────────────────────
// Helper: Build URL with optional base
// ────────────────────────────────────────────────────────────────────────────

function buildUrl(path: string, base?: string): URL {
  if (!base) {
    // Relative URL: construct from current origin
    return new URL(path, typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3001');
  }
  return new URL(path, base);
}

// ────────────────────────────────────────────────────────────────────────────
// Mapper: Convert backend monitor row to SessionRow
// ────────────────────────────────────────────────────────────────────────────

interface MonitorRowRaw {
  call_sid: string;
  ts: number;
  duration_secs: number;
  end_reason?: string;
  outcome?: unknown;
  tenant_id?: string;
  turn_count?: number;
  extra?: Record<string, unknown>;
  [key: string]: unknown;
}

function normalizeSession(row: MonitorRowRaw): SessionRow {
  const timestamp = typeof row.ts === 'number' ? row.ts * 1000 : Date.now();
  const isoString = new Date(timestamp).toISOString();
  const ended_properly = row.end_reason !== 'error' && row.end_reason !== 'disconnect';
  
  // Extract scenario_tags from extra field if present
  const scenario_tags = row.extra?.scenario_tags;

  return {
    call_sid: row.call_sid || '',
    tenant_id: row.tenant_id || 'unknown',
    started_at: isoString,
    duration_seconds: Number(row.duration_secs) || 0,
    turn_count: Number(row.turn_count) || 0,
    ended_properly,
    build_sha: '',
    scenario_tags: scenario_tags as any,  // Will be undefined if not classified yet
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Helper: Typed fetch with error handling
// ────────────────────────────────────────────────────────────────────────────

async function fetchWithTenant<T>(
  path: string,
  tenantId?: string,
): Promise<T> {
  const url = buildUrl(path, API_BASE);
  if (tenantId) {
    url.searchParams.set('tenant', tenantId);
  }
  const resp = await fetch(url.toString());
  if (!resp.ok) {
    throw new Error(`API error: ${resp.status} ${resp.statusText}`);
  }
  return resp.json();
}

// ────────────────────────────────────────────────────────────────────────────
// 1. Monitor overview
// ────────────────────────────────────────────────────────────────────────────

export interface MonitorOverview {
  ok: boolean;
  health_hints: string[];
  snapshot?: unknown;
  config?: unknown;
}

export function useMonitorOverview() {
  return useQuery({
    queryKey: ['monitor-overview'],
    queryFn: () => fetchWithTenant<MonitorOverview>('/api/dashboard/monitor'),
    refetchInterval: 10000,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Recent calls / sessions
// ────────────────────────────────────────────────────────────────────────────

export interface MonitorCallsResponse {
  calls: SessionRow[];
  count: number;
}

export function useMonitorCalls(
  tenantId?: string,
  options?: { window?: number; limit?: number },
) {
  return useQuery({
    queryKey: ['monitor-calls', tenantId, options],
    queryFn: async () => {
      const url = buildUrl('/api/dashboard/monitor/calls', API_BASE);
      if (tenantId) url.searchParams.set('tenant', tenantId);
      if (options?.window) url.searchParams.set('window', String(options.window));
      if (options?.limit) url.searchParams.set('limit', String(options.limit));

      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error(`Failed to fetch calls: ${resp.status}`);
      const json = (await resp.json()) as { calls: MonitorRowRaw[]; count: number };
      
      // Normalize backend monitor rows to SessionRow schema
      return {
        calls: json.calls.map(normalizeSession),
        count: json.count,
      } as MonitorCallsResponse;
    },
    refetchInterval: 3000,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Call turns / historical turn data
// ────────────────────────────────────────────────────────────────────────────

export interface CallTurnsResponse {
  call_sid: string;
  turn_count: number;
  turns: TurnRow[];
}

export function useCallTurns(callSid: string, tenantId?: string) {
  return useQuery({
    queryKey: ['call-turns', callSid, tenantId],
    queryFn: async () => {
      const url = buildUrl(`/api/admin/call/${callSid}/turns`, API_BASE);
      if (tenantId) url.searchParams.set('tenant', tenantId);

      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error(`Failed to fetch turns: ${resp.status}`);
      return resp.json() as Promise<CallTurnsResponse>;
    },
    enabled: !!callSid,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 4. Call report
// ────────────────────────────────────────────────────────────────────────────

export interface CallReport {
  call_sid: string;
  summary: string;
  markdown?: string;
}

export function useCallReport(callSid: string) {
  return useQuery({
    queryKey: ['call-report', callSid],
    queryFn: async () => {
      const url = buildUrl(`/api/dashboard/call-report/${callSid}`, API_BASE);
      url.searchParams.set('format', 'json');

      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error(`Failed to fetch report: ${resp.status}`);
      return resp.json() as Promise<CallReport>;
    },
    enabled: !!callSid,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 5. Live trace events
// ────────────────────────────────────────────────────────────────────────────

export interface LiveTraceResponse {
  events: LiveEvent[];
  call_sid: string;
}

export function useLiveTrace(callSid: string, tenantId?: string) {
  return useQuery({
    queryKey: ['live-trace', callSid, tenantId],
    queryFn: async () => {
      const url = buildUrl(`/api/dashboard/live/${callSid}/trace`, API_BASE);
      if (tenantId) url.searchParams.set('tenant', tenantId);

      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error(`Failed to fetch live trace: ${resp.status}`);
      return resp.json() as Promise<LiveTraceResponse>;
    },
    enabled: !!callSid,
    refetchInterval: 1000,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// 6. Active calls
// ────────────────────────────────────────────────────────────────────────────

export interface ActiveCallsResponse {
  count: number;
}

export function useActiveCalls() {
  return useQuery({
    queryKey: ['active-calls'],
    queryFn: () => fetchWithTenant<ActiveCallsResponse>('/active-calls'),
    refetchInterval: 5000,
  });
}

// ────────────────────────────────────────────────────────────────────────────
// Steering endpoints (Phase 8 — placeholder for now)
// ────────────────────────────────────────────────────────────────────────────

export async function resetCallToTurn(
  callSid: string,
  turnN: number,
): Promise<{ call_sid: string; reset_to_turn: number }> {
  const url = buildUrl(`/api/admin/call/${callSid}/reset`, API_BASE);
  url.searchParams.set('turn', String(turnN));

  const resp = await fetch(url.toString(), { method: 'POST' });
  if (!resp.ok) throw new Error(`Failed to reset: ${resp.status}`);
  return resp.json();
}

export async function forkCall(
  callSid: string,
): Promise<{ new_call_sid: string }> {
  const url = buildUrl(`/api/admin/call/${callSid}/fork`, API_BASE);

  const resp = await fetch(url.toString(), { method: 'POST' });
  if (!resp.ok) throw new Error(`Failed to fork: ${resp.status}`);
  return resp.json();
}

export async function replayCall(
  callSid: string,
  fixedInput?: string,
): Promise<{ replay_call_sid: string }> {
  const url = buildUrl(`/api/admin/call/${callSid}/replay`, API_BASE);
  if (fixedInput) {
    url.searchParams.set('fix_input', fixedInput);
  }

  const resp = await fetch(url.toString(), { method: 'POST' });
  if (!resp.ok) throw new Error(`Failed to replay: ${resp.status}`);
  return resp.json();
}

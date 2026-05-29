'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  Zap,
  Clock,
  Activity,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

interface TraceEvent {
  ts: number;
  phase: string;
  event: string;
  level: string;
  detail?: Record<string, unknown> | null;
}

type LevelType = 'error' | 'warn' | 'info' | 'debug' | string;

const LEVEL_STYLE: Record<string, string> = {
  error: 'bg-[#fff0ee] border-brand-salmon/40 text-brand-salmon',
  warn:  'bg-[#fff8ea] border-yellow-300/40 text-brand-peach',
  info:  'bg-white border-brand-cream text-brand-navy',
  debug: 'bg-[#f9f9f9] border-brand-cream text-brand-muted',
};

const LEVEL_ICON: Record<string, React.ReactNode> = {
  error: <XCircle size={14} className="text-brand-salmon flex-shrink-0" />,
  warn:  <AlertCircle size={14} className="text-brand-peach flex-shrink-0" />,
  info:  <Info size={14} className="text-blue-400 flex-shrink-0" />,
  debug: <ChevronRight size={14} className="text-brand-muted flex-shrink-0" />,
};

const PHASE_COLOR: Record<string, string> = {
  session: 'bg-blue-50 text-blue-600 border-blue-200',
  adk:     'bg-purple-50 text-purple-600 border-purple-200',
  tool:    'bg-yellow-50 text-yellow-700 border-yellow-200',
  pipeline:'bg-red-50 text-red-600 border-red-200',
  gate:    'bg-orange-50 text-orange-600 border-orange-200',
  tier:    'bg-teal-50 text-teal-600 border-teal-200',
};

function EventCard({ ev, idx }: { ev: TraceEvent; idx: number }) {
  const [open, setOpen] = useState(ev.event === 'checkpoint' || ev.level === 'error');
  const hasDetail = ev.detail && Object.keys(ev.detail).length > 0;

  const levelStyle = LEVEL_STYLE[ev.level as LevelType] ?? LEVEL_STYLE.info;
  const levelIcon = LEVEL_ICON[ev.level as LevelType] ?? LEVEL_ICON.info;
  const phaseStyle = PHASE_COLOR[ev.phase] ?? 'bg-brand-cream text-brand-slate border-brand-cream';

  const ts = new Date(ev.ts * 1000).toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });

  return (
    <div className={`border rounded-lg ${levelStyle} overflow-hidden`}>
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer select-none"
        onClick={() => hasDetail && setOpen(!open)}
      >
        <span className="text-xs font-mono text-brand-muted w-8 text-right flex-shrink-0">{idx + 1}</span>
        {levelIcon}
        <span className="text-xs font-mono text-brand-muted flex-shrink-0">{ts}</span>
        <span className={`px-1.5 py-0.5 rounded text-xs font-semibold border ${phaseStyle} flex-shrink-0`}>
          {ev.phase}
        </span>
        <span className="text-sm font-medium flex-1 truncate">{ev.event}</span>
        {hasDetail && (
          open
            ? <ChevronDown size={14} className="text-brand-muted flex-shrink-0" />
            : <ChevronRight size={14} className="text-brand-muted flex-shrink-0" />
        )}
      </div>
      {open && hasDetail && (
        <div className="border-t border-[#e8d8d2]/40 px-4 pb-4 pt-3">
          <pre className="text-xs font-mono text-brand-navy whitespace-pre-wrap break-all overflow-x-auto bg-brand-cream/50 rounded p-3">
            {JSON.stringify(ev.detail, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function TracePage() {
  const params = useParams<{ sid: string }>();
  const search = useSearchParams();
  const router = useRouter();

  const sid = params?.sid ? decodeURIComponent(params.sid) : '';
  const tenant = search?.get('tenant') ?? '';

  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadTrace = useCallback(async () => {
    if (!sid) return;
    setError(null);
    try {
      const qs = tenant ? `?tenant=${encodeURIComponent(tenant)}` : '';
      const res = await fetch(`/api/dashboard/live/${encodeURIComponent(sid)}/trace${qs}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data.events)) setEvents(data.events);
      setLastFetched(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load trace');
    } finally {
      setLoading(false);
    }
  }, [sid, tenant]);

  useEffect(() => {
    loadTrace();
  }, [loadTrace]);

  useEffect(() => {
    if (!autoRefresh) return;
    const iv = setInterval(loadTrace, 3000);
    return () => clearInterval(iv);
  }, [autoRefresh, loadTrace]);

  const checkpoints = events.filter(e => e.event === 'checkpoint');
  const errors = events.filter(e => e.level === 'error');
  const lastCheckpoint = checkpoints[checkpoints.length - 1];

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-4xl mx-auto space-y-5">

        {/* Back + header */}
        <div className="flex items-start gap-4">
          <button
            onClick={() => router.push('/live-calls')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy text-sm transition mt-0.5"
          >
            <ArrowLeft size={14} />
            Back
          </button>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-brand-navy">Call Trace</h1>
            <p className="text-brand-slate text-xs font-mono mt-0.5 break-all">
              {sid}
              {tenant && <span className="ml-2 text-brand-muted">({tenant})</span>}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <label className="flex items-center gap-1.5 cursor-pointer select-none text-xs text-brand-slate">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={e => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto
            </label>
            <button
              onClick={loadTrace}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy text-sm transition"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* Stats bar */}
        {events.length > 0 && (
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-1.5 bg-white border border-brand-cream rounded-lg px-3 py-2">
              <Activity size={14} className="text-brand-pink" />
              <span className="text-brand-navy font-semibold">{events.length}</span>
              <span className="text-brand-muted">events</span>
            </div>
            {errors.length > 0 && (
              <div className="flex items-center gap-1.5 bg-[#fff0ee] border border-brand-salmon/30 rounded-lg px-3 py-2">
                <XCircle size={14} className="text-brand-salmon" />
                <span className="text-brand-salmon font-semibold">{errors.length}</span>
                <span className="text-brand-salmon">errors</span>
              </div>
            )}
            {checkpoints.length > 0 && (
              <div className="flex items-center gap-1.5 bg-[#fff8ea] border border-yellow-200 rounded-lg px-3 py-2">
                <Zap size={14} className="text-brand-peach" />
                <span className="text-brand-peach font-semibold">{checkpoints.length}</span>
                <span className="text-brand-peach">checkpoints</span>
              </div>
            )}
            {lastFetched && (
              <div className="flex items-center gap-1.5 bg-brand-cream rounded-lg px-3 py-2 ml-auto">
                <Clock size={14} className="text-brand-muted" />
                <span className="text-brand-muted text-xs">
                  fetched {lastFetched.toLocaleTimeString('de-DE')}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Last checkpoint highlight */}
        {lastCheckpoint && (
          <div className="bg-[#fff8ea] border border-yellow-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap size={15} className="text-brand-peach" />
              <span className="text-sm font-semibold text-brand-navy">Last checkpoint snapshot</span>
              <span className="ml-auto text-xs font-mono text-brand-muted">
                {new Date(lastCheckpoint.ts * 1000).toLocaleTimeString('de-DE')}
              </span>
            </div>
            {lastCheckpoint.detail && (
              <pre className="text-xs font-mono text-brand-navy whitespace-pre-wrap break-all overflow-x-auto bg-white/70 rounded p-3">
                {JSON.stringify(lastCheckpoint.detail, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-white shadow-sm border border-brand-salmon/30 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle size={18} className="text-brand-salmon flex-shrink-0" />
            <p className="text-brand-salmon text-sm">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw size={22} className="animate-spin text-brand-pink" />
          </div>
        ) : events.length === 0 ? (
          <div className="bg-white shadow-sm border border-brand-cream rounded-lg p-8 text-center">
            <p className="text-brand-muted text-sm mb-2">No trace events found for this call.</p>
            <p className="text-xs text-brand-muted">
              Traces are stored in Redis (TTL 4h). Make sure{' '}
              <code className="bg-brand-cream px-1 rounded">LIVE_TRACE_ENABLE=1</code> is set on the voice agent.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Phase legend */}
            <div className="flex flex-wrap gap-2 py-1">
              {Object.entries(PHASE_COLOR).map(([phase, cls]) => (
                <span key={phase} className={`px-2 py-0.5 rounded text-xs font-semibold border ${cls}`}>
                  {phase}
                </span>
              ))}
            </div>
            {events.map((ev, i) => (
              <EventCard key={i} ev={ev} idx={i} />
            ))}
            <div className="flex items-center justify-center py-4 gap-2 text-brand-muted text-xs">
              <CheckCircle size={14} className="text-[#16a34a]" />
              End of trace — {events.length} events
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

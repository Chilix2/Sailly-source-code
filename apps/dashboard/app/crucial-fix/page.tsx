'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  FlaskConical, CheckCircle2, XCircle, AlertTriangle, Clock, ChevronDown, ChevronRight,
  RefreshCw, Activity, ExternalLink, Play, Square, Pause, Rocket, Ban,
  TrendingUp, BarChart3, Zap,
} from 'lucide-react';

interface ManifestRun {
  index: number;
  code?: string;
  name: string;
  type?: string;
  status: string;
  dir: string;
  started_at?: string;
  finished_at?: string;
  timestamp?: string;
}

type SessionStatus = 'running' | 'paused' | 'finished' | 'failed' | 'interrupted' | 'successfully_deployed' | 'stopped';
type FilterKey = null | 'all' | 'running' | 'successfully_deployed' | 'finished' | 'failed' | 'interrupted' | 'stopped';

interface Session {
  id: string;
  label: string;
  started_at: string;
  finished_at?: string;
  status: SessionStatus;
  phase_a?: ManifestRun;
  fix_iterations: ManifestRun[];
  cfv?: ManifestRun;
  phase_e?: ManifestRun;
  deploy?: ManifestRun;
  pass_rate?: string;
  phase_e_pass_rate?: number;
  failing_count?: number;
  buckets_passed?: number;
  buckets_total?: number;
  currentPhase?: string;
}

interface LoopStatus {
  running?: boolean;
  paused?: boolean;
  phase?: string;
  started_at?: string;
  last_result?: string;
  last_pass_rate?: number;
  current_bucket?: string;
  current_attempt?: number;
  pid?: number;
}

// ── Phase Pipeline ─────────────────────────────────────────────────────────────
const ALL_PHASES = [
  { key: 'phase_a', label: 'Phase A', sublabel: 'Baseline' },
  { key: 'fix_loop', label: 'Fix Loop', sublabel: '1–8 iters' },
  { key: 'cfv', label: 'CFV', sublabel: 'Deep Fix' },
  { key: 'phase_e', label: 'Phase E', sublabel: 'Regression' },
  { key: 'deploy', label: 'Deploy', sublabel: 'Brain → Demo' },
] as const;

type PhaseKey = 'phase_a' | 'fix_loop' | 'cfv' | 'phase_e' | 'deploy';

function getSessionPhaseProgress(session: Session): { key: PhaseKey; status: 'done' | 'running' | 'failed' | 'pending' }[] {
  const allRuns: ManifestRun[] = [
    session.phase_a, ...session.fix_iterations, session.cfv, session.phase_e, session.deploy,
  ].filter(Boolean) as ManifestRun[];

  const hasRunning = allRuns.some(r => r.status === 'running');

  function ps(run?: ManifestRun | null): 'done' | 'running' | 'failed' | 'pending' {
    if (!run) return 'pending';
    if (run.status === 'finished' || run.status === 'completed') return 'done';
    if (run.status === 'running') return 'running';
    if (run.status === 'failed' || run.status === 'stopped' || run.status === 'partial') return 'failed';
    return 'pending';
  }

  const phaseA = ps(session.phase_a);
  let fixLoopStatus: 'done' | 'running' | 'failed' | 'pending' = 'pending';
  if (session.fix_iterations.length > 0) {
    if (session.fix_iterations.some(r => r.status === 'running')) fixLoopStatus = 'running';
    else if (session.cfv || session.phase_e) fixLoopStatus = 'done';
    else if (session.fix_iterations.some(r => r.status === 'failed')) fixLoopStatus = 'failed';
    else fixLoopStatus = 'done';
  } else if (hasRunning && phaseA === 'done' && !session.cfv && !session.phase_e) {
    fixLoopStatus = 'running';
  }

  return [
    { key: 'phase_a', status: phaseA },
    { key: 'fix_loop', status: fixLoopStatus },
    { key: 'cfv', status: ps(session.cfv) },
    { key: 'phase_e', status: ps(session.phase_e) },
    { key: 'deploy', status: ps(session.deploy) },
  ];
}

/** Phase A baseline rows: canonical, patched label, or legacy rows missing `code`. */
function isPhaseABaselineRun(run: ManifestRun): boolean {
  const c = run.code ?? '';
  if (c === 'PHASE-A' || c === 'PHASE-A-PATCHED') return true;
  if (c.startsWith('PHASE-A')) return true;
  if (!c && /phase\s*a/i.test(run.name ?? '')) return true;
  return false;
}

function runLooksFinished(run: ManifestRun): boolean {
  return run.status === 'finished' || run.status === 'completed';
}

function standaloneSessionStatus(run: ManifestRun): SessionStatus {
  if (run.status === 'running') return 'running';
  if (runLooksFinished(run)) return 'finished';
  return 'stopped';
}

function groupRunsIntoSessions(runs: ManifestRun[]): Session[] {
  const sessions: Session[] = [];
  let current: Session | null = null;

  for (const run of runs) {
    if (isPhaseABaselineRun(run)) {
      if (current) sessions.push(current);
      current = {
        id: `session-${sessions.length}`,
        label: extractSessionLabel(run.name),
        started_at: run.started_at || run.timestamp || '',
        status: 'running',
        phase_a: run,
        fix_iterations: [],
      };
    } else if (current) {
      if (run.code?.startsWith('FIX-') || run.code?.startsWith('NO-FIX')) {
        current.fix_iterations.push(run);
        current.finished_at = run.finished_at;
        const m = run.name.match(/(\d+)\s+failing/);
        if (m) current.failing_count = parseInt(m[1]);
      } else if (run.code?.startsWith('CFV')) {
        current.cfv = run;
        current.finished_at = run.finished_at;
      } else if (run.code === 'PHASE-E') {
        current.phase_e = run;
        current.finished_at = run.finished_at;
      } else if (run.code === 'DEPLOY') {
        current.deploy = run;
        current.finished_at = run.finished_at;
      } else if (run.type === 'noautofix_deep' || run.code?.startsWith('NOAUTOFIX')) {
        // Standalone NoAutoFix deep run — create its own session
        if (current) sessions.push(current);
        const nfLabel = extractSessionLabel(run.name) || 'NoAutoFix-Deep';
        sessions.push({
          id: `session-${sessions.length}`,
          label: nfLabel,
          started_at: run.started_at || '',
          finished_at: run.finished_at,
          status: standaloneSessionStatus(run),
          phase_a: run,
          fix_iterations: [],
          pass_rate: run.name.match(/(\d+)%/) ? run.name.match(/(\d+)%/)![1] + '%' : undefined,
        });
        current = null;
        continue;
      }
    } else {
      // Orphan run without a preceding PHASE-A — create standalone session
      if (run.type === 'noautofix_deep' || run.code?.startsWith('NOAUTOFIX')) {
        const nfLabel = extractSessionLabel(run.name) || 'NoAutoFix-Deep';
        sessions.push({
          id: `session-${sessions.length}`,
          label: nfLabel,
          started_at: run.started_at || '',
          finished_at: run.finished_at,
          status: standaloneSessionStatus(run),
          phase_a: run,
          fix_iterations: [],
          pass_rate: run.name.match(/(\d+)%/) ? run.name.match(/(\d+)%/)![1] + '%' : undefined,
        });
      }
    }
  }
  if (current) sessions.push(current);

  for (const session of sessions) {
    const allRuns = [session.phase_a, ...session.fix_iterations, session.cfv, session.phase_e, session.deploy].filter(Boolean) as ManifestRun[];
    const hasRunning = allRuns.some(r => r.status === 'running');
    const hasFailed = allRuns.some(r => r.status === 'failed');
    const hasStopped = allRuns.some(r => r.status === 'stopped');

    // Phase E pass rate
    let phaseEPassRate: number | undefined;
    if (session.phase_e) {
      const m = session.phase_e.name.match(/(\d+(?:\.\d+)?)%/) || session.phase_e.name.match(/(\d+)\/(\d+)/);
      if (m?.[2]) phaseEPassRate = (parseInt(m[1]) / parseInt(m[2])) * 100;
      else if (m) phaseEPassRate = parseFloat(m[1]);
    }
    session.phase_e_pass_rate = phaseEPassRate;

    if (hasRunning) session.status = 'running';
    else if (hasStopped && !session.phase_e) session.status = 'stopped';
    else if ((session.phase_e?.status === 'finished' || session.phase_e?.status === 'completed') && phaseEPassRate !== undefined && phaseEPassRate >= 95)
      session.status = 'successfully_deployed';
    else if (session.phase_e?.status === 'finished' || session.phase_e?.status === 'completed' || session.phase_e?.status === 'failed')
      session.status = 'finished';
    else if (hasFailed && !hasRunning)
      session.status = session.fix_iterations.length >= 8 ? 'interrupted' : 'failed';
    else if (!hasRunning && allRuns.length > 0)
      session.status = 'finished';
    else session.status = 'running';

    if (hasRunning) {
      // Use the LAST running run (most recent phase), not the first
      const runningRuns = allRuns.filter(r => r.status === 'running');
      const r = runningRuns[runningRuns.length - 1];
      if (r) {
        if (isPhaseABaselineRun(r)) session.currentPhase = 'Phase A';
        else if (r.code?.startsWith('FIX-')) session.currentPhase = `Fix ${r.code.replace('FIX-', '')}`;
        else if (r.code?.startsWith('CFV')) session.currentPhase = 'CFV';
        else if (r.code === 'PHASE-E') session.currentPhase = 'Phase E';
        else if (r.code === 'DEPLOY') session.currentPhase = 'Deploy';
      }
    }

    const rm = session.phase_a?.name.match(/(\d+)\/(\d+)/);
    if (rm) {
      const p = parseInt(rm[1]), t = parseInt(rm[2]);
      session.pass_rate = `${((p / t) * 100).toFixed(1)}%`;
      session.buckets_passed = p; session.buckets_total = t;
    }
  }
  return sessions;
}

function extractSessionLabel(name: string): string {
  const m = name.match(/\[([\d-]+(?:\s+#\d+)?)\]/);
  if (m) return m[1];
  const nf = name.match(/\[(NoAutoFix[^\]]*)\]/);
  if (nf) return nf[1];
  const d = name.match(/(\d{4}-\d{2}-\d{2})/);
  if (d) return d[1];
  return '';
}

function statusIcon(status: string, size = 16) {
  if (status === 'successfully_deployed') return <Rocket size={size} className="text-brand-pink" />;
  if (status === 'finished') return <CheckCircle2 size={size} className="text-[#16a34a]" />;
  if (status === 'running') return <RefreshCw size={size} className="text-brand-pink animate-spin" />;
  if (status === 'paused') return <Pause size={size} className="text-amber-500" />;
  if (status === 'stopped') return <Ban size={size} className="text-red-500" />;
  if (status === 'failed') return <XCircle size={size} className="text-brand-salmon" />;
  if (status === 'interrupted') return <AlertTriangle size={size} className="text-amber-500" />;
  if (status === 'partial') return <AlertTriangle size={size} className="text-amber-500" />;
  return <Clock size={size} className="text-brand-muted" />;
}

function statusBadge(status: string) {
  const b = 'text-xs font-semibold px-2 py-0.5 rounded-full';
  if (status === 'successfully_deployed') return <span className={`${b} text-white bg-brand-pink border border-brand-pink`}>Deployed</span>;
  if (status === 'finished') return <span className={`${b} text-[#16a34a] bg-green-50 border border-green-200`}>Finished</span>;
  if (status === 'running') return <span className={`${b} text-brand-pink bg-pink-50 border border-pink-200`}>Running</span>;
  if (status === 'paused') return <span className={`${b} text-amber-600 bg-amber-50 border border-amber-200`}>Paused</span>;
  if (status === 'stopped') return <span className={`${b} text-red-600 bg-red-50 border border-red-200`}>Stopped</span>;
  if (status === 'failed') return <span className={`${b} text-brand-salmon bg-red-50 border border-red-200`}>Failed</span>;
  if (status === 'interrupted') return <span className={`${b} text-amber-600 bg-amber-50 border border-amber-200`}>Interrupted</span>;
  return <span className={`${b} text-brand-muted bg-gray-50 border border-gray-200`}>{status}</span>;
}

function fmtTime(iso?: string) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return iso; }
}

function fmtDur(start?: string, end?: string) {
  if (!start) return '';
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const secs = Math.floor((e - s) / 1000);
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
}

// ── Phase Progress Bar ─────────────────────────────────────────────────────────
function PhaseProgressBar({ session }: { session: Session }) {
  const progress = getSessionPhaseProgress(session);
  return (
    <div className="flex items-center flex-wrap gap-y-1 mt-2">
      {ALL_PHASES.map((phase, i) => {
        const st = progress.find(p => p.key === phase.key)?.status ?? 'pending';
        const colors = {
          done: 'bg-green-50 border-green-200 text-green-700',
          running: 'bg-pink-50 border-brand-pink text-brand-pink',
          failed: 'bg-red-50 border-red-200 text-red-600',
          pending: 'bg-gray-50 border-gray-200 text-gray-400',
        }[st];
        const dot = { done: 'bg-green-500', running: 'bg-brand-pink', failed: 'bg-red-500', pending: 'bg-gray-300' }[st];
        return (
          <div key={phase.key} className="flex items-center">
            <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-xs font-medium whitespace-nowrap ${colors}`}>
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${st === 'running' ? 'animate-pulse' : ''} ${dot}`} />
              <span>{phase.label}</span>
              {phase.key === 'fix_loop' && session.fix_iterations.length > 0 && (
                <span className="opacity-60">({session.fix_iterations.length}/8)</span>
              )}
            </div>
            {i < ALL_PHASES.length - 1 && (
              <div className={`w-3 h-px shrink-0 ${st === 'done' ? 'bg-green-300' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Run Row ────────────────────────────────────────────────────────────────────
function RunRow({ run, sessionIndices }: { run: ManifestRun; sessionIndices: number[] }) {
  // Link to the unified dashboard deep-linked to this specific run, scoped to session
  const indicesParam = sessionIndices.length > 1 ? `&indices=${sessionIndices.join(',')}` : '';
  const link = run.index !== undefined ? `/validation/?run=${run.index}${indicesParam}` : null;
  return (
    <div className="flex items-center gap-2 py-1.5 px-3 text-xs hover:bg-[#f5e9e4]/50 rounded group">
      {statusIcon(run.status, 14)}
      <span className="font-mono text-brand-navy font-semibold w-14 shrink-0">{run.code}</span>
      <span className="text-brand-slate flex-1 truncate min-w-0">{run.name}</span>
      <span className="text-brand-muted shrink-0 tabular-nums">{fmtTime(run.started_at)}</span>
      <span className="text-brand-muted w-14 text-right shrink-0 font-mono tabular-nums">{fmtDur(run.started_at, run.finished_at)}</span>
      {link ? (
        <a href={link} target="_blank" rel="noopener noreferrer"
          className="text-brand-muted hover:text-brand-pink shrink-0 opacity-0 group-hover:opacity-100 transition"
          title="Open in unified dashboard">
          <ExternalLink size={11} />
        </a>
      ) : <span className="w-3 shrink-0" />}
    </div>
  );
}

// ── Session Card ───────────────────────────────────────────────────────────────
interface SessionCardProps {
  session: Session;
  defaultOpen: boolean;
  isRunning: boolean;
  isPaused: boolean;
  onControl: (action: string) => void;
  controlLoading: boolean;
}

function SessionCard({ session, defaultOpen, isRunning, isPaused, onControl, controlLoading }: SessionCardProps) {
  const [open, setOpen] = useState(defaultOpen);

  const allRuns: ManifestRun[] = [
    session.phase_a, ...session.fix_iterations, session.cfv, session.phase_e, session.deploy,
  ].filter(Boolean) as ManifestRun[];

  // Collect all non-null indices for this session to enable scoped navigation
  const allSessionRunIndices = [
    session.phase_a?.index,
    ...session.fix_iterations.map(r => r.index),
    session.cfv?.index,
    session.phase_e?.index,
    session.deploy?.index,
  ].filter(n => n !== undefined) as number[];

  // Link to the unified dashboard starting at this session's first run, scoped to this session
  const firstRunIndex = allSessionRunIndices[0] ?? null;
  const sessionLink = firstRunIndex !== null
    ? `/validation/?run=${firstRunIndex}&indices=${allSessionRunIndices.join(',')}`
    : null;
  const isThisRunning = session.status === 'running';
  const isThisPaused = session.status === 'paused';
  const canControl = isThisRunning || isThisPaused;

  return (
    <div className="bg-white shadow-sm border border-brand-cream rounded-xl overflow-hidden">
      {/* Header row */}
      <div className="flex items-stretch">
        {/* Expand toggle + main info — takes up available space */}
        <button
          onClick={() => setOpen(!open)}
          className="flex-1 flex items-start gap-3 px-4 py-3.5 text-left hover:bg-[#f5e9e4]/20 transition min-w-0"
        >
          <div className="mt-0.5 shrink-0">
            {open ? <ChevronDown size={15} className="text-brand-muted" /> : <ChevronRight size={15} className="text-brand-muted" />}
          </div>
          {statusIcon(session.status)}

          <div className="flex-1 min-w-0">
            {/* Row 1: label + badges */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-brand-navy text-sm">{session.label}</span>
              {statusBadge(session.status)}
              {session.pass_rate && (
                <span className="text-xs text-brand-muted font-mono">Baseline: {session.pass_rate}</span>
              )}
              {session.phase_e_pass_rate !== undefined && (
                <span className={`text-xs font-semibold ${session.phase_e_pass_rate >= 95 ? 'text-green-600' : 'text-brand-salmon'}`}>
                  Final: {session.phase_e_pass_rate.toFixed(1)}%
                </span>
              )}
              {session.currentPhase && (
                <span className="text-xs text-brand-pink font-medium animate-pulse">● {session.currentPhase}</span>
              )}
            </div>

            {/* Row 2: time + duration */}
            <div className="flex items-center gap-2 mt-0.5 text-xs text-brand-muted">
              <Clock size={10} />
              <span>{fmtTime(session.started_at)}</span>
              {session.finished_at && <><span>→</span><span>{fmtTime(session.finished_at)}</span></>}
              {fmtDur(session.started_at, session.finished_at) && (
                <span className="font-mono">{fmtDur(session.started_at, session.finished_at)}</span>
              )}
            </div>

            {/* Phase progress bar */}
            <PhaseProgressBar session={session} />
          </div>
        </button>

        {/* Right-side action panel */}
        <div className="flex flex-col items-end justify-between gap-2 px-4 py-3.5 border-l border-brand-cream shrink-0 min-w-[140px]">
          {/* Metadata badges */}
          <div className="flex flex-wrap justify-end gap-1">
            {session.fix_iterations.length > 0 && (
              <span className="text-xs bg-[#f5e9e4] text-brand-navy px-2 py-0.5 rounded font-medium">
                {session.fix_iterations.length} fix iter
              </span>
            )}
            {session.cfv && (
              <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded font-medium border border-amber-200">CFV</span>
            )}
            {session.phase_e && (
              <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-medium border border-blue-200">Phase E</span>
            )}
            {session.failing_count != null && session.failing_count > 0 && (
              <span className="text-xs text-brand-salmon font-semibold">{session.failing_count} failing</span>
            )}
            <span className="text-xs text-brand-muted">{allRuns.length} runs</span>
          </div>

          {/* Controls / link */}
          <div className="flex items-center gap-1.5">
            {/* Run link */}
            {sessionLink && (
              <a href={sessionLink} target="_blank" rel="noopener noreferrer"
                onClick={e => e.stopPropagation()}
                className="flex items-center gap-1 px-2 py-1 text-xs text-brand-navy hover:text-brand-pink border border-[#e8d8d2] hover:border-brand-pink rounded transition"
                title="Open in unified dashboard">
                <ExternalLink size={11} />
                <span>View</span>
              </a>
            )}

            {/* Control buttons — only shown when this session is the active one */}
            {canControl && isThisRunning && !isPaused && (
              <button onClick={e => { e.stopPropagation(); onControl('pause'); }}
                disabled={controlLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded transition disabled:opacity-50"
                title="Pause">
                <Pause size={11} /> Pause
              </button>
            )}
            {canControl && isPaused && (
              <button onClick={e => { e.stopPropagation(); onControl('continue'); }}
                disabled={controlLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded transition disabled:opacity-50"
                title="Resume">
                <Play size={11} /> Resume
              </button>
            )}
            {canControl && (
              <button onClick={e => {
                e.stopPropagation();
                if (confirm('Stop the running validation loop?')) onControl('stop');
              }}
                disabled={controlLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded transition disabled:opacity-50"
                title="Stop">
                <Square size={11} /> Stop
              </button>
            )}
            {!canControl && !isRunning && (
              <button onClick={e => { e.stopPropagation(); onControl('start'); }}
                disabled={controlLoading}
                className="flex items-center gap-1 px-2 py-1 text-xs text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded transition disabled:opacity-50"
                title="Start new validation run">
                <Play size={11} /> Start
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Expanded run list */}
      {open && allRuns.length > 0 && (
        <div className="border-t border-brand-cream bg-[#faf5f2]/60">
          <div className="px-4 pt-2 pb-0.5 text-xs text-brand-muted font-semibold uppercase tracking-wide">Run Details</div>
          {allRuns.map(run => <RunRow key={`${run.code}-${run.index}`} run={run} sessionIndices={allSessionRunIndices} />)}
        </div>
      )}
    </div>
  );
}

// ── KPI Card ───────────────────────────────────────────────────────────────────
interface KpiCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  filterKey: FilterKey;
  activeFilter: FilterKey;
  onClick: (k: FilterKey) => void;
  sessions: Session[];
  color: string;
}

function KpiCard({ label, value, icon, filterKey, activeFilter, onClick, sessions, color }: KpiCardProps) {
  const isActive = filterKey !== null && filterKey !== 'all' && activeFilter === filterKey;
  const subset = (filterKey && filterKey !== 'all')
    ? sessions.filter(s => {
        if (filterKey === 'failed') return s.status === 'failed' || s.status === 'interrupted' || s.status === 'stopped';
        if (filterKey === 'finished') return s.status === 'finished';
        if (filterKey === 'successfully_deployed') return s.status === 'successfully_deployed';
        if (filterKey === 'running') return s.status === 'running' || s.status === 'paused';
        return true;
      })
    : [];

  return (
    <button
      onClick={() => onClick(isActive ? null : filterKey)}
      className={`bg-white shadow-sm rounded-xl p-4 text-left w-full transition hover:shadow-md ${
        isActive ? 'ring-2 ring-brand-pink border-brand-pink border' : 'border border-brand-cream'
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs text-brand-slate uppercase tracking-wide">{label}</p>
        <span className="text-brand-muted">{icon}</span>
      </div>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {isActive && subset.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {subset.slice(0, 4).map(s => (
            <p key={s.id} className="text-xs text-brand-slate truncate">· {s.label}</p>
          ))}
          {subset.length > 4 && <p className="text-xs text-brand-muted">+ {subset.length - 4} more</p>}
        </div>
      )}
      {isActive && subset.length === 0 && (
        <p className="mt-1 text-xs text-brand-muted italic">None in this category</p>
      )}
    </button>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────
export default function ValidationRunsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loopStatus, setLoopStatus] = useState<LoopStatus | null>(null);
  const [totalRuns, setTotalRuns] = useState(0);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [controlLoading, setControlLoading] = useState(false);
  const [controlMsg, setControlMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [filterStatus, setFilterStatus] = useState<FilterKey>(null);

  const loadData = useCallback(async () => {
    try {
      const [mRes, sRes] = await Promise.all([
        fetch('/validation/runs_manifest.json?t=' + Date.now()),
        fetch('/validation/heal_loop_status.json?t=' + Date.now()),
      ]);
      if (mRes.ok) {
        const manifest = await mRes.json();
        const runs: ManifestRun[] = manifest.runs ?? manifest ?? [];
        setSessions(groupRunsIntoSessions(runs));
        setTotalRuns(runs.length);
      }
      if (sRes.ok) setLoopStatus(await sRes.json());
      setLastUpdated(new Date());
    } catch { /* ignore */ } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    loadData();
    const iv = setInterval(loadData, 15_000);
    return () => clearInterval(iv);
  }, [loadData]);

  const sendControl = async (action: string) => {
    setControlLoading(true);
    setControlMsg(null);
    try {
      const res = await fetch('/api/validation/control', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setControlMsg({ type: 'success', text: data.message || `${action} succeeded` });
        setTimeout(loadData, 1000);
      } else {
        setControlMsg({ type: 'error', text: data.error || `${action} failed` });
      }
    } catch { setControlMsg({ type: 'error', text: 'Network error' }); }
    finally {
      setControlLoading(false);
      setTimeout(() => setControlMsg(null), 5000);
    }
  };

  const isRunning = loopStatus?.running === true;
  const isPaused = loopStatus?.paused === true;
  const isCfv = isRunning && loopStatus?.phase?.includes('CFV');

  // Stats
  const deployedCount = sessions.filter(s => s.status === 'successfully_deployed').length;
  const finishedCount = sessions.filter(s => s.status === 'finished').length;
  const failedCount = sessions.filter(s => ['failed', 'interrupted', 'stopped'].includes(s.status)).length;
  const runningCount = sessions.filter(s => s.status === 'running' || s.status === 'paused').length;

  // Filtered sessions
  const filteredSessions = filterStatus
    ? sessions.filter(s => {
        if (filterStatus === 'failed') return ['failed', 'interrupted', 'stopped'].includes(s.status);
        if (filterStatus === 'running') return s.status === 'running' || s.status === 'paused';
        return s.status === filterStatus;
      })
    : sessions;

  return (
    <div className="min-h-screen bg-transparent p-6 md:p-8">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* ── Page Header ── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-brand-navy flex items-center gap-2">
              <FlaskConical size={24} className="text-brand-pink shrink-0" />
              Validation Runs
            </h1>
            <p className="text-xs text-brand-muted mt-0.5">
              Phase A → Fix Loop → CFV → Phase E → Deploy (ADK Brain update)
              {lastUpdated && <span className="ml-2">· {lastUpdated.toLocaleTimeString('de-DE')}</span>}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Live status pill */}
            {isRunning && (
              <span className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-full border ${
                isPaused ? 'text-amber-700 bg-amber-50 border-amber-200'
                  : isCfv ? 'text-amber-700 bg-amber-50 border-amber-200'
                  : 'text-emerald-700 bg-emerald-50 border-emerald-200'
              }`}>
                <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-amber-400' : isCfv ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'}`} />
                {isPaused ? 'Paused'
                  : isCfv ? (loopStatus?.current_bucket ? `CFV: ${loopStatus.current_bucket}` : 'CFV Active')
                  : (loopStatus?.phase || 'Running')}
              </span>
            )}
            {/* Refresh only */}
            <button onClick={loadData}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-cream hover:bg-[#dfcdc7] border border-[#e8d8d2] rounded-lg text-brand-navy text-sm transition">
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* ── Control feedback ── */}
        {controlMsg && (
          <div className={`px-4 py-2.5 rounded-lg text-sm font-medium border ${
            controlMsg.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
          }`}>
            {controlMsg.text}
          </div>
        )}

        {/* ── Active run banner ── */}
        {isRunning && loopStatus?.phase && (
          <div className={`px-4 py-2.5 rounded-xl border flex items-center gap-3 ${isPaused ? 'bg-amber-50 border-amber-200' : 'bg-emerald-50 border-emerald-200'}`}>
            {isPaused
              ? <Pause size={16} className="text-amber-600 shrink-0" />
              : <Activity size={16} className="text-emerald-600 shrink-0 animate-pulse" />}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-semibold ${isPaused ? 'text-amber-700' : 'text-emerald-700'}`}>
                {isPaused ? 'Validation Paused' : 'Validation Running'}
              </p>
              <p className={`text-xs truncate ${isPaused ? 'text-amber-600' : 'text-emerald-600'}`}>
                {loopStatus.phase}
                {loopStatus.current_bucket && ` — Bucket: ${loopStatus.current_bucket}`}
                {loopStatus.current_attempt !== undefined && ` (attempt ${loopStatus.current_attempt})`}
              </p>
            </div>
            {/* Global controls in banner */}
            <div className="flex items-center gap-1.5 shrink-0">
              {!isPaused && (
                <button onClick={() => sendControl('pause')} disabled={controlLoading}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs text-amber-700 bg-amber-100 hover:bg-amber-200 border border-amber-300 rounded transition disabled:opacity-50">
                  <Pause size={11} /> Pause
                </button>
              )}
              {isPaused && (
                <button onClick={() => sendControl('continue')} disabled={controlLoading}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs text-emerald-700 bg-emerald-100 hover:bg-emerald-200 border border-emerald-300 rounded transition disabled:opacity-50">
                  <Play size={11} /> Resume
                </button>
              )}
              <button onClick={() => { if (confirm('Stop the running validation loop?')) sendControl('stop'); }}
                disabled={controlLoading}
                className="flex items-center gap-1 px-2.5 py-1 text-xs text-red-700 bg-red-100 hover:bg-red-200 border border-red-300 rounded transition disabled:opacity-50">
                <Square size={11} /> Stop
              </button>
            </div>
          </div>
        )}

        {/* ── KPI Cards (clickable filters) ── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard label="Sessions" value={sessions.length}
            icon={<BarChart3 size={14} />} filterKey="all" activeFilter={filterStatus}
            onClick={() => setFilterStatus(null)} sessions={sessions} color="text-brand-navy" />
          <KpiCard label="Total Runs" value={totalRuns}
            icon={<Zap size={14} />} filterKey="all" activeFilter={filterStatus}
            onClick={() => setFilterStatus(null)} sessions={sessions} color="text-brand-pink" />
          <KpiCard label="Deployed" value={deployedCount}
            icon={<Rocket size={14} />} filterKey="successfully_deployed" activeFilter={filterStatus}
            onClick={setFilterStatus} sessions={sessions} color="text-brand-pink" />
          <KpiCard label="Finished" value={finishedCount}
            icon={<CheckCircle2 size={14} />} filterKey="finished" activeFilter={filterStatus}
            onClick={setFilterStatus} sessions={sessions} color="text-[#16a34a]" />
          <KpiCard label="Failed" value={failedCount}
            icon={<TrendingUp size={14} />} filterKey="failed" activeFilter={filterStatus}
            onClick={setFilterStatus} sessions={sessions} color="text-brand-salmon" />
        </div>

        {/* Filter indicator */}
        {filterStatus && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-brand-muted">
              Showing {filteredSessions.length} of {sessions.length} sessions
            </span>
            <button onClick={() => setFilterStatus(null)}
              className="text-xs text-brand-pink hover:underline">Clear filter</button>
          </div>
        )}

        {/* ── Session List ── */}
        <div className="space-y-2.5">
          {loading && sessions.length === 0 ? (
            <div className="flex items-center justify-center py-16">
              <RefreshCw size={24} className="animate-spin text-brand-pink" />
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="bg-white shadow-sm border border-brand-cream rounded-xl p-8 text-center">
              <FlaskConical size={32} className="text-brand-muted mx-auto mb-3" />
              <p className="text-brand-muted">
                {filterStatus ? 'No sessions match this filter.' : 'No validation runs found.'}
              </p>
            </div>
          ) : (
            [...filteredSessions].reverse().map((session, i) => (
              <SessionCard
                key={session.id}
                session={session}
                defaultOpen={i === 0}
                isRunning={isRunning}
                isPaused={isPaused}
                onControl={sendControl}
                controlLoading={controlLoading}
              />
            ))
          )}
        </div>

        {/* ── Legend ── */}
        <div className="bg-white shadow-sm border border-brand-cream rounded-xl p-4">
          <p className="text-xs font-semibold text-brand-navy mb-2 uppercase tracking-wide">Legend</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-brand-slate">
            <div className="flex items-center gap-1.5"><Rocket size={11} className="text-brand-pink shrink-0" /> Deployed — Phase E ≥95%, brain updated</div>
            <div className="flex items-center gap-1.5"><CheckCircle2 size={11} className="text-green-600 shrink-0" /> Finished — Phase E ran, &lt;95% threshold</div>
            <div className="flex items-center gap-1.5"><AlertTriangle size={11} className="text-amber-500 shrink-0" /> Interrupted — 8 fix iterations exhausted</div>
            <div className="flex items-center gap-1.5"><XCircle size={11} className="text-red-500 shrink-0" /> Failed / Stopped — aborted early</div>
          </div>
          <p className="mt-2 text-xs text-brand-muted">Deploy copies ADK brain files to sailly-browser-demo, restarts services, runs 5-scenario smoke test, then monitors 30-min canary window.</p>
        </div>
      </div>
    </div>
  );
}

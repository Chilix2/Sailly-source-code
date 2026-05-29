import { NextResponse } from 'next/server';
import { readFileSync, existsSync } from 'fs';

const MANIFEST_PATH = '/tmp/validation_runs/runs_manifest.json';
const STATUS_PATH = '/tmp/validation_runs/heal_loop_status.json';

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

function isPhaseABaselineRun(run: ManifestRun): boolean {
  const c = run.code ?? '';
  if (c === 'PHASE-A' || c === 'PHASE-A-PATCHED') return true;
  if (c.startsWith('PHASE-A')) return true;
  if (!c && /phase\s*a/i.test(run.name ?? '')) return true;
  return false;
}

interface Session {
  id: string;
  label: string;
  started_at: string;
  finished_at?: string;
  status: 'running' | 'finished' | 'failed' | 'interrupted';
  phase_a?: ManifestRun;
  fix_iterations: ManifestRun[];
  cfv?: ManifestRun;
  phase_e?: ManifestRun;
  pass_rate?: string;
  failing_count?: number;
  buckets_passed?: number;
  buckets_total?: number;
}

function groupRunsIntoSessions(runs: ManifestRun[]): Session[] {
  const sessions: Session[] = [];
  let current: Session | null = null;

  for (const run of runs) {
    if (isPhaseABaselineRun(run)) {
      // New session starts with each Phase A
      if (current) sessions.push(current);
      const label = extractSessionLabel(run.name);
      current = {
        id: `session-${sessions.length}`,
        label,
        started_at: run.started_at || run.timestamp || '',
        status: 'running',
        phase_a: run,
        fix_iterations: [],
      };
    } else if (current) {
      if (run.code?.startsWith('FIX-')) {
        current.fix_iterations.push(run);
        current.finished_at = run.finished_at;
        // Extract failing count from name
        const failMatch = run.name.match(/(\d+)\s+failing/);
        if (failMatch) current.failing_count = parseInt(failMatch[1]);
      } else if (run.code?.startsWith('CFV')) {
        current.cfv = run;
        current.finished_at = run.finished_at;
      } else if (run.code === 'PHASE-E') {
        current.phase_e = run;
        current.finished_at = run.finished_at;
      }
    }
  }
  if (current) sessions.push(current);

  // Determine session status
  for (const session of sessions) {
    const allRuns = [
      session.phase_a,
      ...session.fix_iterations,
      session.cfv,
      session.phase_e,
    ].filter(Boolean) as ManifestRun[];

    const hasRunning = allRuns.some(r => r.status === 'running');
    const hasFailed = allRuns.some(r => r.status === 'failed');

    if (hasRunning) {
      session.status = 'running';
    } else if (session.phase_e?.status === 'finished' || session.phase_e?.status === 'completed') {
      session.status = 'finished';
    } else if (hasFailed && !hasRunning) {
      session.status = session.fix_iterations.length >= 8 ? 'interrupted' : 'failed';
    } else {
      session.status = 'finished';
    }

    // Extract pass rate from Phase A name
    const rateMatch = session.phase_a?.name.match(/(\d+)\/(\d+)/);
    if (rateMatch) {
      const passed = parseInt(rateMatch[1]);
      const total = parseInt(rateMatch[2]);
      session.pass_rate = `${((passed / total) * 100).toFixed(1)}%`;
      session.buckets_passed = passed;
      session.buckets_total = total;
    }
  }

  return sessions;
}

function extractSessionLabel(name: string): string {
  // Try to extract date + sequence from names like "[2026-04-09 #8]"
  const m = name.match(/\[([\d-]+(?:\s+#\d+)?)\]/);
  if (m) return m[1];
  // Fallback: extract date
  const d = name.match(/(\d{4}-\d{2}-\d{2})/);
  if (d) return d[1];
  return 'Unknown';
}

export async function GET() {
  try {
    let runs: ManifestRun[] = [];
    if (existsSync(MANIFEST_PATH)) {
      const raw = JSON.parse(readFileSync(MANIFEST_PATH, 'utf-8'));
      runs = raw.runs ?? raw ?? [];
    }

    let loopStatus = null;
    if (existsSync(STATUS_PATH)) {
      loopStatus = JSON.parse(readFileSync(STATUS_PATH, 'utf-8'));
    }

    const sessions = groupRunsIntoSessions(runs);

    return NextResponse.json({
      totalRuns: runs.length,
      sessions,
      loopStatus,
      runs,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Failed to read validation data' },
      { status: 500 }
    );
  }
}

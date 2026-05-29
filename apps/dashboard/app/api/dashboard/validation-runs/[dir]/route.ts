import { NextRequest, NextResponse } from 'next/server';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const RUNS_ROOT = '/tmp/validation_runs';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ dir: string }> }
) {
  const { dir } = await params;
  const decoded = decodeURIComponent(dir).replace(/\.\./g, '');
  const runDir = join(RUNS_ROOT, decoded);

  if (!existsSync(runDir)) {
    return NextResponse.json({ error: 'Run directory not found' }, { status: 404 });
  }

  const result: Record<string, unknown> = { dir: decoded };

  // Try to load fix validation state
  const fvStatePath = join(runDir, 'fix_validation_state.json');
  if (existsSync(fvStatePath)) {
    result.fixValidationState = JSON.parse(readFileSync(fvStatePath, 'utf-8'));
  }

  // Try to load ab results
  const abPath = join(runDir, 'ab_results.json');
  if (existsSync(abPath)) {
    result.abResults = JSON.parse(readFileSync(abPath, 'utf-8'));
  }

  // Try to load CFV state
  const cfvPath = join(runDir, 'cfv_state.json');
  if (existsSync(cfvPath)) {
    result.cfvState = JSON.parse(readFileSync(cfvPath, 'utf-8'));
  }

  return NextResponse.json(result);
}

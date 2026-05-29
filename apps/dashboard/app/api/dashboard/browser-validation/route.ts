import { NextRequest, NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

// GET /api/dashboard/browser-validation
// Returns latest validation run + recent history
export async function GET(request: NextRequest) {
    try {
        const pool = getDbPool();
        
        // Latest run
        const latestRes = await pool.query(`
            SELECT * FROM browser_validation_runs 
            ORDER BY started_at DESC LIMIT 1
        `);
        const latestRun = latestRes.rows[0] || null;
        
        // Recent history (last 20 runs)
        const historyRes = await pool.query(`
            SELECT id, run_id, bucket, started_at, status, total_scenarios, 
                   passed_count, pass_rate, phase_a_baseline, pipeline_gap
            FROM browser_validation_runs 
            ORDER BY started_at DESC LIMIT 20
        `);
        
        // If there's a latest run, fetch its results
        let scenarios = [];
        if (latestRun) {
            const resultsRes = await pool.query(`
                SELECT scenario_id, passed, composite_score, tools_expected, 
                       tools_got, tools_missing, failure_reasons, turn_count
                FROM browser_validation_results 
                WHERE run_id = $1 
                ORDER BY passed ASC, scenario_id ASC
            `, [latestRun.run_id]);
            scenarios = resultsRes.rows;
        }
        
        return NextResponse.json({
            latestRun,
            scenarios,
            history: historyRes.rows,
            stats: {
                totalRuns: historyRes.rowCount,
                avgPassRate: calculateAvgPassRate(historyRes.rows),
            }
        });
    } catch (error) {
        console.error('[Browser Validation API] Error:', error);
        return NextResponse.json({ error: 'Failed to fetch validation data' }, { status: 500 });
    }
}

// POST /api/dashboard/browser-validation/trigger
// Trigger a validation run from the dashboard
export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { bucket = 'smoke' } = body;
        
        // Execute the script in background
        const { spawn } = require('child_process');
        
        spawn('/home/charles2/scripts/run_browser_validation.sh', [bucket], {
            detached: true,
            stdio: 'ignore'
        }).unref();
        
        return NextResponse.json({
            status: 'started',
            bucket,
            message: `Validation started for bucket: ${bucket}`
        });
    } catch (error) {
        console.error('[Browser Validation Trigger] Error:', error);
        return NextResponse.json({ error: 'Failed to trigger validation' }, { status: 500 });
    }
}

function calculateAvgPassRate(runs: any[]): number {
    if (runs.length === 0) return 0;
    const sum = runs.reduce((acc, run) => acc + (run.pass_rate || 0), 0);
    return sum / runs.length;
}

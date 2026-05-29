import { NextRequest, NextResponse } from 'next/server';
import { getDbPool } from '@/lib/db';

// GET /api/dashboard/browser-validation/[runId]
// Returns full details for a specific run
export async function GET(
    request: NextRequest,
    { params }: { params: { runId: string } }
) {
    try {
        const pool = getDbPool();
        const { runId } = params;
        
        const runRes = await pool.query(
            'SELECT * FROM browser_validation_runs WHERE run_id = $1',
            [runId]
        );
        const run = runRes.rows[0];
        
        if (!run) {
            return NextResponse.json({ error: 'Run not found' }, { status: 404 });
        }
        
        const resultsRes = await pool.query(`
            SELECT * FROM browser_validation_results 
            WHERE run_id = $1 
            ORDER BY passed ASC, composite_score DESC
        `, [runId]);
        
        const passedCount = resultsRes.rows.filter(r => r.passed).length;
        const totalCount = resultsRes.rowCount || 0;
        const passRate = totalCount > 0 ? (passedCount / totalCount * 100).toFixed(1) : '0';
        
        return NextResponse.json({
            run,
            results: resultsRes.rows,
            summary: {
                total: totalCount,
                passed: passedCount,
                failed: totalCount - passedCount,
                passRate: parseFloat(passRate as string),
            }
        });
    } catch (error) {
        console.error('[Browser Validation Detail] Error:', error);
        return NextResponse.json({ error: 'Failed to fetch run details' }, { status: 500 });
    }
}

import { NextResponse } from 'next/server';
import fs from 'fs';

const STATUS_FILE = '/tmp/validation_runs/heal_loop_status.json';

export async function GET() {
  try {
    if (!fs.existsSync(STATUS_FILE)) {
      return NextResponse.json({ running: false, phase: '', next_scheduled: '' });
    }
    const raw = fs.readFileSync(STATUS_FILE, 'utf-8');
    const data = JSON.parse(raw);
    return NextResponse.json({
      running: data.running === true,
      phase: data.phase ?? '',
      last_result: data.last_result ?? '',
      last_pass_rate: data.last_pass_rate ?? 0,
      last_completed: data.last_completed ?? '',
      next_scheduled: data.next_scheduled ?? '',
      updated_at: data.updated_at ?? '',
    });
  } catch {
    return NextResponse.json({ running: false, phase: '', next_scheduled: '' });
  }
}

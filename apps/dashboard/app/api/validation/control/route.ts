import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execAsync = promisify(exec);

const LOCK_FILE = '/tmp/validation_heal_loop.lock';
const STATUS_FILE = '/tmp/validation_runs/heal_loop_status.json';
const CONTROL_FILE = '/tmp/validation_runs/control_signal.json';

async function getValidationPid(): Promise<number | null> {
  // Method 1: Try lock file (contains fd, not PID directly — find process holding it)
  try {
    const { stdout } = await execAsync(
      `lsof ${LOCK_FILE} 2>/dev/null | grep -v COMMAND | awk '{print $2}' | head -1`
    );
    const pid = parseInt(stdout.trim());
    if (!isNaN(pid) && pid > 0) return pid;
  } catch { /* ignore */ }

  // Method 2: Find by process name
  try {
    const { stdout } = await execAsync(
      `pgrep -f 'validation_heal_loop' 2>/dev/null | head -1`
    );
    const pid = parseInt(stdout.trim());
    if (!isNaN(pid) && pid > 0) return pid;
  } catch { /* ignore */ }

  return null;
}

async function isProcessRunning(pid: number): Promise<boolean> {
  try {
    await execAsync(`kill -0 ${pid} 2>/dev/null`);
    return true;
  } catch {
    return false;
  }
}

function readStatus(): Record<string, unknown> {
  try {
    if (!fs.existsSync(STATUS_FILE)) return { running: false, phase: '', paused: false };
    return JSON.parse(fs.readFileSync(STATUS_FILE, 'utf-8'));
  } catch {
    return { running: false, phase: '', paused: false };
  }
}

function writeControlSignal(action: string, reason?: string) {
  try {
    const control = {
      action,
      reason: reason || '',
      timestamp: new Date().toISOString(),
    };
    fs.mkdirSync('/tmp/validation_runs', { recursive: true });
    fs.writeFileSync(CONTROL_FILE, JSON.stringify(control, null, 2));
  } catch { /* ignore */ }
}

function clearControlSignal() {
  try {
    if (fs.existsSync(CONTROL_FILE)) fs.unlinkSync(CONTROL_FILE);
  } catch { /* ignore */ }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action, reason } = body as { action: string; reason?: string };

    if (!['start', 'stop', 'pause', 'continue', 'status'].includes(action)) {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }

    const currentStatus = readStatus();
    const pid = await getValidationPid();
    const isRunning = pid ? await isProcessRunning(pid) : false;

    if (action === 'status') {
      return NextResponse.json({
        running: isRunning,
        pid,
        paused: currentStatus.paused ?? false,
        phase: currentStatus.phase ?? '',
        status: currentStatus,
      });
    }

    if (action === 'stop') {
      writeControlSignal('stop', reason || 'Manual stop via dashboard');

      if (pid && isRunning) {
        try {
          await execAsync(`kill -TERM ${pid}`);
          await new Promise(resolve => setTimeout(resolve, 2000));
          // Force kill if still running
          const stillRunning = await isProcessRunning(pid);
          if (stillRunning) {
            await execAsync(`kill -KILL ${pid}`);
          }
        } catch { /* ignore */ }
      }

      // Update status file to reflect stop
      try {
        const status = readStatus();
        status.running = false;
        status.paused = false;
        status.last_result = 'stopped';
        status.updated_at = new Date().toISOString();
        fs.writeFileSync(STATUS_FILE, JSON.stringify(status, null, 2));
      } catch { /* ignore */ }

      clearControlSignal();
      return NextResponse.json({ success: true, action: 'stop', message: 'Validation loop stopped' });
    }

    if (action === 'pause') {
      if (!pid || !isRunning) {
        return NextResponse.json({ error: 'No validation process is running' }, { status: 400 });
      }

      writeControlSignal('pause', reason || 'Manual pause via dashboard');

      try {
        await execAsync(`kill -STOP ${pid}`);

        // Update status file to reflect pause
        const status = readStatus();
        status.paused = true;
        status.updated_at = new Date().toISOString();
        fs.writeFileSync(STATUS_FILE, JSON.stringify(status, null, 2));

        return NextResponse.json({ success: true, action: 'pause', message: 'Validation loop paused', pid });
      } catch (err) {
        return NextResponse.json({ error: `Failed to pause: ${err}` }, { status: 500 });
      }
    }

    if (action === 'continue') {
      if (!pid) {
        return NextResponse.json({ error: 'No validation process found' }, { status: 400 });
      }

      clearControlSignal();

      try {
        await execAsync(`kill -CONT ${pid}`);

        // Update status file to reflect resume
        const status = readStatus();
        status.paused = false;
        status.updated_at = new Date().toISOString();
        fs.writeFileSync(STATUS_FILE, JSON.stringify(status, null, 2));

        return NextResponse.json({ success: true, action: 'continue', message: 'Validation loop resumed', pid });
      } catch (err) {
        return NextResponse.json({ error: `Failed to resume: ${err}` }, { status: 500 });
      }
    }

    if (action === 'start') {
      if (isRunning) {
        return NextResponse.json({ error: 'Validation loop is already running', pid }, { status: 400 });
      }

      // Start validation loop as background process, running as charles2 to avoid permission conflicts
      try {
        const venvPython = '/home/charles2/sailly-google-fork/.venv/bin/python3';
        const workDir = '/home/charles2/sailly-google-fork';
        const logFile = '/tmp/validation_runs/manual_start.log';
        const cmd = `cd ${workDir} && nohup ${venvPython} -m server.training.validation_heal_loop --skip-full-validation --results-dir /tmp/ab_heal_results >> ${logFile} 2>&1 &`;

        await execAsync(cmd, { shell: '/bin/bash' });

        return NextResponse.json({ success: true, action: 'start', message: 'Validation loop started' });
      } catch (err) {
        return NextResponse.json({ error: `Failed to start: ${err}` }, { status: 500 });
      }
    }

    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
  } catch (err) {
    console.error('Control API error:', err);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

export async function GET() {
  try {
    const currentStatus = readStatus();
    const pid = await getValidationPid();
    const isRunning = pid ? await isProcessRunning(pid) : false;

    return NextResponse.json({
      running: isRunning,
      pid: pid ?? null,
      paused: currentStatus.paused ?? false,
      phase: currentStatus.phase ?? '',
      status: currentStatus,
    });
  } catch (err) {
    return NextResponse.json({ error: 'Failed to get status' }, { status: 500 });
  }
}

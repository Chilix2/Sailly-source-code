import { FsmState } from '@/types/sailly-debugger';

export const FSM_STATES: FsmState[] = [
  'GREETING',
  'INFO',
  'ORDER_OR_RESERVE',
  'READBACK',
  'COMMITTED',
  'POST_COMMIT',
];

export const FSM_STATE_COLORS: Record<FsmState, string> = {
  GREETING: '#8b5cf6', // purple
  INFO: '#3b82f6', // blue
  ORDER_OR_RESERVE: '#f59e0b', // amber
  READBACK: '#ec4899', // pink
  COMMITTED: '#10b981', // emerald
  POST_COMMIT: '#6366f1', // indigo
};

export const FSM_STATE_LABELS: Record<FsmState, string> = {
  GREETING: 'Greeting',
  INFO: 'Info',
  ORDER_OR_RESERVE: 'Order / Reserve',
  READBACK: 'Readback',
  COMMITTED: 'Committed',
  POST_COMMIT: 'Post-Commit',
};

export function getStateColor(state: FsmState | string | null): string {
  if (!state) return '#94a3b8'; // slate
  return FSM_STATE_COLORS[state as FsmState] || '#94a3b8';
}

export function getStateLabel(state: FsmState | string | null): string {
  if (!state) return 'Unknown';
  return FSM_STATE_LABELS[state as FsmState] || state;
}

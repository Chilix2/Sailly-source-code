import { TurnRow } from '@/types/sailly-debugger';
import { LayerNumber } from '@/lib/store/debugger-store';

export type FieldKind =
  | 'text'
  | 'mono'
  | 'number'
  | 'chips'
  | 'validators'
  | 'warnings'
  | 'bool'
  | 'json';

export interface LayerField {
  key: string;
  label: string;
  kind: FieldKind;
  value: unknown;
  preview: string;
  /** Whether this field is genuinely produced by the backend today. */
  tracked: boolean;
  /** Short reason shown when a field is not tracked / not exposed yet. */
  note?: string;
}

export interface LayerMeta {
  title: string;
  subtitle: string;
}

export const LAYER_META: Record<LayerNumber, LayerMeta> = {
  1: { title: 'Layer 1: Orchestrator', subtitle: 'FSM state, forced commits, validators' },
  2: { title: 'Layer 2: LLM', subtitle: 'Raw model response and text pipeline' },
  3: { title: 'Layer 3: Policy', subtitle: 'Warnings, tool changes, TTS guardrails' },
};

const NOT_TRACKED = 'not tracked yet';

export function toCode(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function preview(value: unknown, empty = '—'): string {
  if (value === null || value === undefined || value === '') return empty;
  if (Array.isArray(value)) return value.length ? value.join(', ') : empty;
  if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>);
    return keys.length ? `${keys.length} field${keys.length > 1 ? 's' : ''}` : empty;
  }
  if (typeof value === 'string' && value.length > 40) return value.slice(0, 40) + '…';
  return String(value);
}

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined || value === '') return true;
  if (Array.isArray(value)) return value.length === 0;
  return false;
}

/**
 * Build the field list for every layer of a turn. `tracked` reflects whether
 * the backend genuinely populates the field today (see backend research); the
 * UI shows a "not tracked yet" tag for untracked-and-empty fields.
 */
export function buildLayerFields(turn: TurnRow): Record<LayerNumber, LayerField[]> {
  const l1 = turn.layer1_decision;
  const l3 = turn.layer3_changes;

  const f = (
    key: string,
    label: string,
    kind: FieldKind,
    value: unknown,
    tracked: boolean,
    note?: string,
    emptyLabel = '—'
  ): LayerField => ({
    key,
    label,
    kind,
    value,
    preview: !tracked && isEmpty(value) ? NOT_TRACKED : preview(value, emptyLabel),
    tracked: tracked || !isEmpty(value),
    note,
  });

  return {
    1: [
      f('fsm_node', 'FSM node', 'text', turn.node_name || l1?.node || null, true),
      f('state_hash', 'State hash', 'mono', l1?.state_hash ?? null, true, undefined, 'not recorded'),
      f('forced_tools', 'Forced tools', 'chips', l1?.forced_tools ?? [], false, 'Pipeline does not emit forced_tools yet'),
      f('validators', 'Validators', 'validators', l1?.validators_run ?? [], false, 'Validator registry does not run yet'),
      f('layer1_decision', 'Raw Layer 1 decision', 'json', l1 ?? null, true),
    ],
    2: [
      f('llm_latency_ms', 'LLM latency (ms)', 'number', turn.llm_latency_ms ?? null, true),
      f('layer2_raw_output', 'Raw model output', 'text', turn.layer2_raw_output ?? null, true, 'Currently mirrors the final bot text'),
      f('stage1_clean_text', 'Stage 1 clean text', 'text', turn.stage1_clean_text ?? null, false, 'Stage 1 text not captured yet'),
      f('stage2_clean_text', 'Stage 2 clean text', 'text', turn.stage2_clean_text ?? null, false, 'Stage 2 text not captured yet'),
      f('stage3_text', 'Final stage text', 'text', turn.stage3_text ?? null, false, 'Not exposed by the turns API yet'),
    ],
    3: [
      f('warnings', 'Warnings', 'warnings', l3?.warnings ?? [], false, 'Policy warnings not emitted yet'),
      f('text_changed', 'Text changed', 'bool', l3?.text_changed ?? null, false, 'Policy text-rewrite flag not emitted yet'),
      f('tools_changed', 'Tools changed', 'bool', l3?.tools_changed ?? null, false, 'Policy tool-gating flag not emitted yet'),
      f('tools_called', 'Tools called', 'chips', turn.tools_called ?? [], true, undefined, 'none'),
      f('tts_situation', 'TTS situation', 'text', turn.tts_situation ?? null, false, 'Not exposed by the turns API yet'),
      f('tts_mood', 'TTS mood', 'text', turn.tts_mood ?? null, false, 'Not exposed by the turns API yet'),
      f('tts_suppressed_reason', 'TTS suppressed', 'text', turn.tts_suppressed_reason ?? null, false, 'TTS suppression reason not tracked yet'),
      f('layer3_changes', 'Raw Layer 3 changes', 'json', l3 ?? null, true),
    ],
  };
}

export function findField(
  turn: TurnRow,
  layer: LayerNumber,
  key: string
): LayerField | undefined {
  return buildLayerFields(turn)[layer].find((field) => field.key === key);
}

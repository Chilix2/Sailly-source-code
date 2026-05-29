'use client';

import React from 'react';
import { Workflow, Gauge, AlertTriangle } from 'lucide-react';
import { useDebuggerStore, LayerNumber } from '@/lib/store/debugger-store';
import { LAYER_META } from '@/lib/builder/layer-fields';

const ICONS: Record<LayerNumber, React.ReactNode> = {
  1: <Workflow size={16} />,
  2: <Gauge size={16} />,
  3: <AlertTriangle size={16} />,
};

export function LayerSelector() {
  const { selectedLayer, setSelectedLayer, selectedTurnIdx } = useDebuggerStore();
  const active: LayerNumber = selectedLayer ?? 1;
  const layers: LayerNumber[] = [1, 2, 3];

  return (
    <div className="p-3">
      <div className="mb-2 flex items-center justify-between px-1">
        <span className="text-[10px] font-bold uppercase tracking-widest text-brand-muted">
          Layers
        </span>
        <span className="text-[10px] text-brand-muted">
          {selectedTurnIdx !== null ? `Turn ${selectedTurnIdx + 1}` : 'no turn'}
        </span>
      </div>
      <div className="space-y-2">
        {layers.map((layer) => {
          const meta = LAYER_META[layer];
          const isActive = active === layer;
          return (
            <button
              key={layer}
              type="button"
              onClick={() => setSelectedLayer(layer)}
              className={`flex w-full items-start gap-2 rounded-xl border px-3 py-2.5 text-left transition ${
                isActive
                  ? 'border-brand-pink bg-white shadow-sm ring-1 ring-brand-pink/40'
                  : 'border-[#e8d8d2] bg-white/60 hover:bg-white'
              }`}
            >
              <span
                className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg ${
                  isActive ? 'bg-brand-pink text-white' : 'bg-brand-cream text-brand-pink'
                }`}
              >
                {ICONS[layer]}
              </span>
              <span className="min-w-0">
                <span className="block text-xs font-bold text-brand-navy">
                  {meta.title}
                </span>
                <span className="block text-[10px] leading-tight text-brand-muted">
                  {meta.subtitle}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

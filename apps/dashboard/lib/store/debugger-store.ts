import { create } from 'zustand';

export type DebuggerView = 'fsm-flow' | 'tree' | 'timeline' | 'golden' | 'steering' | 'root-cause';

export type LayerNumber = 1 | 2 | 3;

export interface InspectedItem {
  layer: LayerNumber;
  turnIdx: number;
  key: string;
  label: string;
}

interface DebuggerStore {
  selectedTenantId: string | null;
  setSelectedTenantId: (tenant: string | null) => void;

  selectedCallSid: string | null;
  setSelectedCallSid: (sid: string | null) => void;

  selectedTurnIdx: number | null;
  setSelectedTurnIdx: (idx: number | null) => void;

  selectedLayer: LayerNumber | null;
  setSelectedLayer: (layer: LayerNumber | null) => void;

  inspectedItem: InspectedItem | null;
  setInspectedItem: (item: InspectedItem | null) => void;

  currentView: DebuggerView;
  setCurrentView: (view: DebuggerView) => void;

  searchQuery: string;
  setSearchQuery: (query: string) => void;

  showLiveOnly: boolean;
  setShowLiveOnly: (live: boolean) => void;

  wholeCallMode: boolean;
  setWholeCallMode: (whole: boolean) => void;
}

export const useDebuggerStore = create<DebuggerStore>((set) => ({
  selectedTenantId: 'doboo',
  setSelectedTenantId: (tenant) => set({ selectedTenantId: tenant }),

  selectedCallSid: null,
  setSelectedCallSid: (sid) =>
    set({ selectedCallSid: sid, selectedTurnIdx: null, inspectedItem: null }),

  selectedTurnIdx: null,
  setSelectedTurnIdx: (idx) => set({ selectedTurnIdx: idx, inspectedItem: null }),

  selectedLayer: null,
  setSelectedLayer: (layer) => set({ selectedLayer: layer }),

  inspectedItem: null,
  setInspectedItem: (item) =>
    set({ inspectedItem: item, selectedLayer: item ? item.layer : null }),

  currentView: 'fsm-flow',
  setCurrentView: (view) => set({ currentView: view }),

  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  showLiveOnly: false,
  setShowLiveOnly: (live) => set({ showLiveOnly: live }),

  wholeCallMode: false,
  setWholeCallMode: (whole) => set({ wholeCallMode: whole }),
}));

import { create } from 'zustand'

export const useStore = create((set) => ({
  selectedTicker: 'AAPL',
  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

  metrics: null,
  setMetrics: (metrics) => set({ metrics }),

  alerts: [],
  setAlerts: (alerts) => set({ alerts }),

  reconnectStatus: null, // 'reconnecting' | null
  setReconnectStatus: (status) => set({ reconnectStatus: status }),
}))

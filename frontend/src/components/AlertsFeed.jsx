import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '../store'
import { fetchAlerts } from '../api'

const SEVERITY_COLOR = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/50',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/50',
  medium: 'bg-amber-500/20 text-amber-400 border-amber-500/50',
}

export function AlertsFeed() {
  const selectedTicker = useStore((s) => s.selectedTicker)
  const [filterTicker, setFilterTicker] = React.useState(false)
  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => fetchAlerts(50),
    refetchInterval: 10_000,
  })

  const filtered = filterTicker ? alerts.filter((a) => a.ticker === selectedTicker) : alerts.slice(0, 50)

  return (
    <div className="rounded-lg bg-slate-800/50 p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold text-slate-200">Alerts</h2>
        <button
          type="button"
          onClick={() => setFilterTicker((f) => !f)}
          className="text-xs text-slate-400 hover:text-slate-300"
        >
          {filterTicker ? `Filter: ${selectedTicker}` : 'Show all'}
        </button>
      </div>
      {isLoading ? (
        <div className="text-slate-500 text-sm">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="text-slate-500 text-sm">No alerts</div>
      ) : (
        <ul className="space-y-2 max-h-64 overflow-y-auto">
          {filtered.map((alert, i) => (
            <li
              key={`${alert.ticker}-${alert.ts}-${i}`}
              className={`rounded border p-2 text-sm ${SEVERITY_COLOR[alert.severity] || 'bg-slate-700/50 text-slate-400 border-slate-600'}`}
            >
              <span className="font-mono font-medium">{alert.ticker}</span>
              <span className="mx-1">—</span>
              <span>{alert.type}</span>
              {alert.value != null && <span className="ml-1">({(alert.value * 100).toFixed(0)}%)</span>}
              <span className="block text-xs opacity-80 mt-0.5">{alert.ts}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

import { useQuery } from '@tanstack/react-query'
import { useStore } from '../store'
import { fetchTickers, fetchMetrics } from '../api'

export function TickerBar() {
  const selectedTicker = useStore((s) => s.selectedTicker)
  const setSelectedTicker = useStore((s) => s.setSelectedTicker)
  const reconnectStatus = useStore((s) => s.reconnectStatus)

  const { data: tickersData } = useQuery({ queryKey: ['tickers'], queryFn: fetchTickers })
  const tickers = tickersData?.tickers || []

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg bg-slate-800/50 px-4 py-2">
      {reconnectStatus && (
        <span className="rounded bg-amber-500/20 px-2 py-0.5 text-amber-400 text-sm">
          Reconnecting...
        </span>
      )}
      {tickers.map((sym) => (
        <TickerChip
          key={sym}
          symbol={sym}
          isSelected={sym === selectedTicker}
          onSelect={() => setSelectedTicker(sym)}
        />
      ))}
    </div>
  )
}

function TickerChip({ symbol, isSelected, onSelect }) {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics', symbol],
    queryFn: () => fetchMetrics(symbol),
    refetchInterval: 1000,
    enabled: !!symbol,
  })

  const price = metrics?.price
  const display = price != null ? `$${Number(price).toFixed(2)}` : (isLoading ? '…' : '—')

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
        isSelected
          ? 'bg-indigo-600 text-white'
          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
      }`}
    >
      <span className="font-mono">{symbol}</span>
      <span className="ml-2 text-slate-400">{display}</span>
    </button>
  )
}

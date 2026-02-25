import { useQuery } from '@tanstack/react-query'
import { fetchTopMovers } from '../api'

export function Leaderboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['topMovers'],
    queryFn: fetchTopMovers,
    refetchInterval: 60_000,
  })

  if (isLoading) {
    return (
      <div className="rounded-lg bg-slate-800/50 p-4">
        <h2 className="text-lg font-semibold text-slate-200 mb-2">Top Gainers / Losers</h2>
        <div className="animate-pulse space-y-2">
          <div className="h-8 bg-slate-700 rounded" />
          <div className="h-8 bg-slate-700 rounded" />
          <div className="h-8 bg-slate-700 rounded" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg bg-slate-800/50 p-4">
        <h2 className="text-lg font-semibold text-slate-200 mb-2">Top Gainers / Losers</h2>
        <p className="text-slate-500 text-sm">No report data yet. Run the nightly batch job.</p>
      </div>
    )
  }

  const gainers = data.gainers || []
  const losers = data.losers || []
  const generatedAt = data.generated_at

  return (
    <div className="rounded-lg bg-slate-800/50 p-4">
      <h2 className="text-lg font-semibold text-slate-200 mb-2">Top Gainers / Losers</h2>
      {generatedAt && (
        <p className="text-slate-500 text-xs mb-3">Last updated: {generatedAt}</p>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h3 className="text-green-400 text-sm font-medium mb-1">Top 5 Gainers</h3>
          <ul className="space-y-1">
            {(gainers.length ? gainers : [{ symbol: '—', pct_change: 0 }]).slice(0, 5).map((r, i) => (
              <li key={r.symbol || i} className="text-sm text-slate-300 flex justify-between">
                <span className="font-mono">{r.symbol}</span>
                <span className="text-green-400">+{Number(r.pct_change || 0).toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-red-400 text-sm font-medium mb-1">Top 5 Losers</h3>
          <ul className="space-y-1">
            {(losers.length ? losers : [{ symbol: '—', pct_change: 0 }]).slice(0, 5).map((r, i) => (
              <li key={r.symbol || i} className="text-sm text-slate-300 flex justify-between">
                <span className="font-mono">{r.symbol}</span>
                <span className="text-red-400">{Number(r.pct_change || 0).toFixed(2)}%</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}

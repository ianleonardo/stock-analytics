import { useMemo } from 'react'
import { useStore } from '../store'

export function IndicatorsPanel({ ticker }) {
  const metrics = useStore((s) => s.metrics)

  const ts = metrics?.ts ? Number(metrics.ts) : null
  const lastUpdated = useMemo(() => {
    if (!ts) return null
    const d = new Date(ts)
    return d.toLocaleTimeString()
  }, [ts])
  const isStale = ts ? Date.now() - ts > 10_000 : true

  return (
    <div className="rounded-lg bg-slate-800/50 p-4 space-y-4">
      <h2 className="text-lg font-semibold text-slate-200">Indicators — {ticker}</h2>

      <div className="grid gap-3">
        <Card title="Price" value={metrics?.price != null ? `$${Number(metrics.price).toFixed(2)}` : '—'} />
        <Card title="VWAP (1m)" value={metrics?.vwap_1m != null ? `$${Number(metrics.vwap_1m).toFixed(2)}` : '—'} />
        <Card
          title="EMA-9 / EMA-21"
          value={
            metrics?.ema9 != null && metrics?.ema21 != null
              ? `$${Number(metrics.ema9).toFixed(2)} / $${Number(metrics.ema21).toFixed(2)}`
              : '—'
          }
          badge={metrics?.ema9 != null && metrics?.ema21 != null && metrics.ema9 > metrics.ema21 ? 'Bullish' : 'Bearish'}
        />
        <Card title="Volatility" value={metrics?.vol != null ? Number(metrics.vol).toFixed(4) : '—'} />
      </div>

      <div className={`text-sm ${isStale ? 'text-amber-400' : 'text-slate-500'}`}>
        Last updated: {lastUpdated ?? '—'} {isStale && '(stale)'}
      </div>
    </div>
  )
}

function Card({ title, value, badge }) {
  return (
    <div className="rounded bg-slate-700/50 p-3">
      <div className="text-slate-400 text-xs uppercase tracking-wide">{title}</div>
      <div className="font-mono text-slate-100 mt-1">{value}</div>
      {badge && (
        <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${badge === 'Bullish' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
          {badge}
        </span>
      )}
    </div>
  )
}

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchHistorical } from '../api'

export function VolumeChart({ ticker }) {
  const { data: historical = [] } = useQuery({
    queryKey: ['historical', ticker],
    queryFn: () => fetchHistorical(ticker, 200),
    enabled: !!ticker,
  })

  const barData = useMemo(() => {
    return historical
      .slice()
      .reverse()
      .map((d) => ({
        date: d.date,
        volume: d.volume,
        fill: d.close >= d.open ? '#22c55e' : '#ef4444',
      }))
  }, [historical])

  return (
    <div className="rounded-lg bg-slate-800/50 p-2">
      <div className="text-slate-400 text-sm mb-1">{ticker} — Volume</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={barData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} />
          <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <Bar dataKey="volume" fill="#475569" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

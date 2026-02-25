import { useEffect, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createChart } from 'lightweight-charts'
import { useStore } from '../store'
import { fetchHistorical } from '../api'

export function CandlestickChart({ ticker }) {
  const chartRef = useRef(null)
  const chartInstance = useRef(null)
  const candlestickSeries = useRef(null)
  const vwapSeries = useRef(null)
  const metrics = useStore((s) => s.metrics)

  const { data: historical = [] } = useQuery({
    queryKey: ['historical', ticker],
    queryFn: () => fetchHistorical(ticker, 200),
    enabled: !!ticker,
  })

  const candleData = useMemo(() => {
    return historical
      .slice()
      .reverse()
      .map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
  }, [historical])

  useEffect(() => {
    if (!chartRef.current || !ticker) return
    const chart = createChart(chartRef.current, {
      layout: { background: { color: '#1e293b' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: '#334155' }, horzLines: { color: '#334155' } },
      width: chartRef.current.clientWidth,
      height: 400,
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: '#475569' },
    })
    chartInstance.current = chart
    candlestickSeries.current = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
    })
    vwapSeries.current = chart.addLineSeries({ color: '#a78bfa', lineWidth: 2 })
    return () => {
      chart.remove()
      chartInstance.current = null
      candlestickSeries.current = null
      vwapSeries.current = null
    }
  }, [ticker])

  useEffect(() => {
    if (!candlestickSeries.current || !candleData.length) return
    candlestickSeries.current.setData(candleData)
  }, [candleData])

  useEffect(() => {
    if (!vwapSeries.current || !candleData.length) return
    const vwapData = candleData.map((c, i) => ({
      time: c.time,
      value: (c.open + c.high + c.low + c.close) / 4,
    }))
    vwapSeries.current.setData(vwapData)
  }, [candleData])

  useEffect(() => {
    if (!chartInstance.current) return
    chartInstance.current.applyOptions({ width: chartRef.current?.clientWidth ?? 0 })
  }, [metrics])

  return (
    <div className="rounded-lg bg-slate-800/50 p-2">
      <div className="text-slate-400 text-sm mb-1">{ticker} — Candlestick + VWAP</div>
      <div ref={chartRef} className="w-full" style={{ height: 400 }} />
    </div>
  )
}

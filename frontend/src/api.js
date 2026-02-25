const API_BASE = import.meta.env.VITE_API_URL || ''

export async function fetchTickers() {
  const r = await fetch(`${API_BASE}/api/tickers`)
  if (!r.ok) throw new Error('Failed to fetch tickers')
  return r.json()
}

export async function fetchMetrics(ticker) {
  const r = await fetch(`${API_BASE}/api/metrics/${ticker}`)
  if (!r.ok) throw new Error(`No metrics for ${ticker}`)
  return r.json()
}

export async function fetchHistorical(ticker, limit = 200) {
  const r = await fetch(`${API_BASE}/api/historical/${ticker}?limit=${limit}`)
  if (!r.ok) throw new Error(`No historical for ${ticker}`)
  return r.json()
}

export async function fetchTopMovers() {
  const r = await fetch(`${API_BASE}/api/reports/top-movers`)
  if (!r.ok) throw new Error('Failed to fetch top movers')
  return r.json()
}

export async function fetchAlerts(limit = 100) {
  const r = await fetch(`${API_BASE}/api/alerts?limit=${limit}`)
  if (!r.ok) throw new Error('Failed to fetch alerts')
  return r.json()
}

export function wsLiveUrl() {
  const base = import.meta.env.VITE_WS_URL || (API_BASE ? new URL(API_BASE).origin.replace(/^http/, 'ws') : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`)
  return `${base}/ws/live`
}

import { useQuery } from '@tanstack/react-query'
import { useStore } from './store'
import { useMarketSocket } from './hooks/useMarketSocket'
import { fetchTickers, fetchTopMovers, fetchAlerts } from './api'
import { TickerBar } from './components/TickerBar'
import { CandlestickChart } from './components/CandlestickChart'
import { VolumeChart } from './components/VolumeChart'
import { IndicatorsPanel } from './components/IndicatorsPanel'
import { AlertsFeed } from './components/AlertsFeed'
import { Leaderboard } from './components/Leaderboard'

function App() {
  const selectedTicker = useStore((s) => s.selectedTicker)
  useMarketSocket(selectedTicker)

  useQuery({
    queryKey: ['tickers'],
    queryFn: fetchTickers,
  })
  useQuery({
    queryKey: ['topMovers'],
    queryFn: fetchTopMovers,
    refetchInterval: 60_000,
  })
  useQuery({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
    refetchInterval: 10_000,
  })

  return (
    <div className="min-h-screen p-4">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-slate-100">Stock Analytics</h1>
        <TickerBar />
      </header>
      <main className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <CandlestickChart ticker={selectedTicker} />
          <VolumeChart ticker={selectedTicker} />
          <div className="grid gap-4 md:grid-cols-2">
            <AlertsFeed />
            <Leaderboard />
          </div>
        </div>
        <IndicatorsPanel ticker={selectedTicker} />
      </main>
    </div>
  )
}

export default App

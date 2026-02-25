import { useEffect, useRef, useCallback } from 'react'
import { useStore } from '../store'
import { wsLiveUrl } from '../api'

const MAX_RETRIES = 5
const BACKOFF_BASE = 1000

export function useMarketSocket(ticker) {
  const wsRef = useRef(null)
  const retryCount = useRef(0)
  const setMetrics = useStore((s) => s.setMetrics)
  const setReconnectStatus = useStore((s) => s.setReconnectStatus)

  const connect = useCallback(() => {
    if (!ticker) return
    const url = wsLiveUrl()
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      retryCount.current = 0
      setReconnectStatus(null)
      ws.send(JSON.stringify({ ticker }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setMetrics(data)
      } catch (_) {}
    }

    ws.onerror = () => {}
    ws.onclose = () => {
      wsRef.current = null
      if (retryCount.current >= MAX_RETRIES) {
        setReconnectStatus(null)
        return
      }
      setReconnectStatus('reconnecting')
      const delay = BACKOFF_BASE * Math.pow(2, retryCount.current)
      retryCount.current += 1
      setTimeout(() => connect(), Math.min(delay, 30000))
    }
  }, [ticker, setMetrics, setReconnectStatus])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setReconnectStatus(null)
    }
  }, [connect])

  return { reconnectStatus: useStore((s) => s.reconnectStatus) }
}

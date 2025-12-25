import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import TradeForm from '../components/TradeForm'
import OrdersTable from '../components/OrdersTable'
import PositionsCard from '../components/PositionsCard'

export default function Symbol() {
  const { symbol } = useParams<{ symbol: string }>()
  const [snapshot, setSnapshot] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSnapshot = async () => {
    if (!symbol) return

    try {
      setLoading(true)
      setError(null)
      const data = await api.getSymbolSnapshot(symbol)
      setSnapshot(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch snapshot')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSnapshot()
    const interval = setInterval(fetchSnapshot, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [symbol])

  if (loading && !snapshot) {
    return (
      <div className="text-center py-8">
        <div className="text-green-400 text-2xl font-bold text-glow animate-pulse-glow">
          ⚡ Loading {symbol}...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-400 text-xl font-bold text-glow animate-pulse-glow">
          ⚠️ Error: {error}
        </div>
      </div>
    )
  }

  if (!snapshot) {
    return (
      <div className="text-center py-8">
        <div className="text-green-400 text-xl text-glow">No data available</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-black/50 border border-green-500/30 p-6 rounded-lg shadow-lg shadow-green-500/20">
        <h1 className="text-3xl font-bold mb-4 text-green-400 text-glow-strong animate-pulse-glow">
          💎 {symbol}
        </h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-black/30 p-4 rounded border border-green-500/20">
            <div className="text-sm text-green-500 mb-1 text-glow">Spot Price</div>
            <div className="text-xl font-bold text-green-300 font-mono animate-number-flash">
              ${snapshot.spot_price?.toFixed(4)}
            </div>
          </div>
          <div className="bg-black/30 p-4 rounded border border-green-500/20">
            <div className="text-sm text-green-500 mb-1 text-glow">Perp Price</div>
            <div className="text-xl font-bold text-green-300 font-mono animate-number-flash">
              ${snapshot.perp_price?.toFixed(4)}
            </div>
          </div>
          <div className="bg-black/30 p-4 rounded border border-green-500/20">
            <div className="text-sm text-green-500 mb-1 text-glow">Funding Rate</div>
            <div className={`text-xl font-bold font-mono animate-number-flash ${
              snapshot.funding_rate > 0 
                ? 'text-green-400 text-glow-strong' 
                : snapshot.funding_rate < -0.01
                ? 'text-cyan-400 text-glow-strong'
                : 'text-red-400'
            }`}>
              {(snapshot.funding_rate_percent || 0).toFixed(4)}%
            </div>
          </div>
          <div className="bg-black/30 p-4 rounded border border-green-500/20">
            <div className="text-sm text-green-500 mb-1 text-glow">Spread (bps)</div>
            <div className="text-xl font-bold text-green-400 animate-number-flash">
              {snapshot.spread_bps?.toFixed(2)}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TradeForm
          symbol={symbol!}
          spotPrice={snapshot.spot_price}
          perpPrice={snapshot.perp_price}
          onSuccess={fetchSnapshot}
        />

        <PositionsCard symbol={symbol} />
      </div>

      <OrdersTable symbol={symbol} />
    </div>
  )
}

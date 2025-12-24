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
    return <div className="text-center py-8">Loading...</div>
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">Error: {error}</div>
  }

  if (!snapshot) {
    return <div className="text-center py-8">No data available</div>
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-4">{symbol}</h1>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-600">Spot Price</div>
            <div className="text-lg font-semibold">${snapshot.spot_price?.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Perp Price</div>
            <div className="text-lg font-semibold">${snapshot.perp_price?.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Funding Rate</div>
            <div className={`text-lg font-semibold ${
              snapshot.funding_rate > 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {(snapshot.funding_rate_percent || 0).toFixed(4)}%
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Spread (bps)</div>
            <div className="text-lg font-semibold">{snapshot.spread_bps?.toFixed(2)}</div>
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

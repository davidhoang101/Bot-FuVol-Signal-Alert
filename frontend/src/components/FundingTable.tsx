import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

interface FundingOpportunity {
  symbol: string
  funding_rate: number
  funding_rate_percent: number
  next_funding_time: number | null
  spot_price: number
  perp_price: number
  basis_pct: number
  spread_bps: number
  orderbook_spread_bps: number
  volume_24h: number
}

interface FundingTableProps {
  minRate?: number
  maxSpreadBps?: number
  autoRefresh?: boolean
  refreshInterval?: number
}

export default function FundingTable({
  minRate,
  maxSpreadBps,
  autoRefresh = false,
  refreshInterval = 10000,
}: FundingTableProps) {
  const [data, setData] = useState<FundingOpportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.getFundingOpportunities({
        min_rate: minRate,
        max_spread_bps: maxSpreadBps,
        exclude_low_volume: true,
      })
      setData(response.results || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [minRate, maxSpreadBps])

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchData, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const formatFundingRate = (rate: number) => {
    return `${(rate * 100).toFixed(4)}%`
  }

  const formatTime = (timestamp: number | null) => {
    if (!timestamp) return 'N/A'
    return new Date(timestamp).toLocaleTimeString()
  }

  if (loading && data.length === 0) {
    return <div className="text-center py-8">Loading...</div>
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">Error: {error}</div>
  }

  return (
    <div className="overflow-x-auto">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Funding Opportunities</h2>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Funding Rate</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Next Funding</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Spot Price</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Perp Price</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Basis %</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Spread (bps)</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">24h Volume</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.map((item) => (
            <tr
              key={item.symbol}
              className="hover:bg-gray-50 cursor-pointer"
              onClick={() => navigate(`/symbol/${item.symbol}`)}
            >
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {item.symbol}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <span className={item.funding_rate > 0 ? 'text-green-600' : 'text-red-600'}>
                  {formatFundingRate(item.funding_rate)}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatTime(item.next_funding_time)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${item.spot_price.toFixed(4)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                ${item.perp_price.toFixed(4)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {item.basis_pct.toFixed(4)}%
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {item.spread_bps.toFixed(2)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${(item.volume_24h / 1e6).toFixed(2)}M
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && !loading && (
        <div className="text-center py-8 text-gray-500">No opportunities found</div>
      )}
    </div>
  )
}

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
    return (
      <div className="text-center py-8">
        <div className="text-green-400 text-2xl font-bold text-glow animate-pulse-glow">
          ⚡ Loading opportunities...
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

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) return `$${(volume / 1e9).toFixed(2)}B`
    if (volume >= 1e6) return `$${(volume / 1e6).toFixed(2)}M`
    if (volume >= 1e3) return `$${(volume / 1e3).toFixed(2)}K`
    return `$${volume.toFixed(2)}`
  }

  return (
    <div className="overflow-x-auto">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-green-400 text-glow animate-pulse-glow">
          💰 Funding Opportunities
        </h2>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-green-600 text-black font-bold rounded hover:bg-green-500 hover-glow transition-all animate-bounce-in"
        >
          🔄 Refresh
        </button>
      </div>

      <div className="bg-black/50 border border-green-500/30 rounded-lg shadow-lg shadow-green-500/20 overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-green-900/30 border-b border-green-500/30">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Symbol</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Funding Rate</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Next Funding</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Spot Price</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Perp Price</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Basis %</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">Spread (bps)</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">📊 24h Volume</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">💰 Est. Profit (1k$)</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-green-400 uppercase text-glow">⚠️ Est. Loss (1k$)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-green-500/20">
            {data.map((item, index) => (
              <tr
                key={item.symbol}
                className="hover:bg-green-900/20 cursor-pointer transition-all animate-slide-up border-l-2 border-transparent hover:border-green-500"
                style={{ animationDelay: `${index * 0.05}s` }}
                onClick={() => navigate(`/symbol/${item.symbol}`)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-green-300 text-glow">
                  {item.symbol}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className={`font-bold text-lg animate-number-flash ${
                    item.funding_rate > 0 
                      ? 'text-green-400' 
                      : item.funding_rate < -0.01
                      ? 'text-cyan-400 text-glow-strong'
                      : 'text-red-400'
                  }`}>
                    {formatFundingRate(item.funding_rate)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-500">
                  {formatTime(item.next_funding_time)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-300 font-mono">
                  ${item.spot_price.toFixed(4)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-300 font-mono">
                  ${item.perp_price.toFixed(4)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-400">
                  {item.basis_pct.toFixed(4)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-400">
                  {item.spread_bps.toFixed(2)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span className="font-bold text-green-400 text-glow animate-volume-pulse inline-block">
                    {formatVolume(item.volume_24h)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {(() => {
                    const orderSize = 1000; // 1k USD
                    // With delta-neutral: Long spot + Short perp
                    // If funding rate positive: Short receives → Profit
                    // If funding rate negative: Short pays → But if we reverse to Long perp, we receive → Profit
                    const fundingRate = item.funding_rate;
                    let estimatedProfit;
                    
                    if (fundingRate > 0) {
                      // Positive funding: Short perp receives → Profit
                      estimatedProfit = orderSize * fundingRate;
                    } else {
                      // Negative funding: Short perp pays → Loss
                      // But if we reverse to Long perp, we receive → Profit
                      estimatedProfit = Math.abs(orderSize * fundingRate);
                    }
                    
                    return (
                      <span className="font-bold text-lg font-mono animate-number-flash text-green-400">
                        +${estimatedProfit.toFixed(2)}
                      </span>
                    );
                  })()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {(() => {
                    const orderSize = 1000; // 1k USD
                    // Loss is the opposite of profit
                    // If funding rate positive: Short receives (profit), but Long perp would pay (loss)
                    // If funding rate negative: Short pays (loss), but Long perp would receive (profit)
                    const fundingRate = item.funding_rate;
                    let estimatedLoss;
                    
                    if (fundingRate > 0) {
                      // Positive funding: If we do Long perp instead of Short → Loss
                      estimatedLoss = orderSize * fundingRate;
                    } else {
                      // Negative funding: If we do Short perp → Loss (pays)
                      estimatedLoss = Math.abs(orderSize * fundingRate);
                    }
                    
                    return (
                      <span className="font-bold text-lg font-mono animate-number-flash text-red-400">
                        -${estimatedLoss.toFixed(2)}
                      </span>
                    );
                  })()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.length === 0 && !loading && (
        <div className="text-center py-8 text-green-500 text-xl animate-pulse-glow">
          ⚠️ No opportunities found
        </div>
      )}
    </div>
  )
}

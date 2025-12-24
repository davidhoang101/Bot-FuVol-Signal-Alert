import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface MarginInfo {
  total_margin: number
  free_margin: number
  used_margin: number
  margin_ratio: number
  free_margin_pct: number
  total_balance: number
}

export default function MarginCard() {
  const [marginInfo, setMarginInfo] = useState<MarginInfo | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMargin = async () => {
    try {
      setLoading(true)
      const response = await api.getMargin()
      setMarginInfo(response)
    } catch (err) {
      console.error('Failed to fetch margin info:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMargin()
    const interval = setInterval(fetchMargin, 5000) // Poll every 5 seconds
    return () => clearInterval(interval)
  }, [])

  if (loading && !marginInfo) {
    return <div className="text-center py-4">Loading margin info...</div>
  }

  if (!marginInfo) {
    return <div className="text-center py-4 text-gray-500">No margin data</div>
  }

  const isLowMargin = marginInfo.free_margin_pct < 30

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Margin Information</h3>

      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">Free Margin</span>
            <span className={`font-medium ${isLowMargin ? 'text-red-600' : 'text-green-600'}`}>
              {marginInfo.free_margin_pct.toFixed(2)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${isLowMargin ? 'bg-red-500' : 'bg-green-500'}`}
              style={{ width: `${marginInfo.free_margin_pct}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-600">Total Balance</div>
            <div className="font-medium">${marginInfo.total_balance.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-gray-600">Used Margin</div>
            <div className="font-medium">${marginInfo.used_margin.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-gray-600">Free Margin</div>
            <div className="font-medium">${marginInfo.free_margin.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-gray-600">Margin Ratio</div>
            <div className="font-medium">{marginInfo.margin_ratio.toFixed(2)}%</div>
          </div>
        </div>
      </div>
    </div>
  )
}

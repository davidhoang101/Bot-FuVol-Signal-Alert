import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface Position {
  symbol: string
  side: string
  size: number
  entry_price: number
  mark_price: number
  unrealized_pnl: number
  percentage: number
  leverage: number
}

export default function PositionsCard({ symbol }: { symbol?: string }) {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)

  const fetchPositions = async () => {
    try {
      setLoading(true)
      const response = await api.getPositions({ symbol })
      setPositions(response.positions || [])
    } catch (err) {
      console.error('Failed to fetch positions:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPositions()
    const interval = setInterval(fetchPositions, 3000) // Poll every 3 seconds
    return () => clearInterval(interval)
  }, [symbol])

  if (loading && positions.length === 0) {
    return <div className="text-center py-4">Loading positions...</div>
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Positions</h3>

      {positions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No open positions</div>
      ) : (
        <div className="space-y-4">
          {positions.map((pos) => (
            <div key={pos.symbol} className="border border-gray-200 rounded p-4">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="font-medium">{pos.symbol}</span>
                  <span className={`ml-2 px-2 py-1 rounded text-xs ${
                    pos.side === 'long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {pos.side.toUpperCase()}
                  </span>
                </div>
                <span className={`text-sm font-medium ${
                  pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                <div>Size: {pos.size.toFixed(6)}</div>
                <div>Entry: ${pos.entry_price.toFixed(4)}</div>
                <div>Mark: ${pos.mark_price.toFixed(4)}</div>
                <div>P&L: {pos.percentage.toFixed(2)}%</div>
                <div>Leverage: {pos.leverage}x</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

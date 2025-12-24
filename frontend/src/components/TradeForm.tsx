import { useState } from 'react'
import { api } from '../api/client'

interface TradeFormProps {
  symbol: string
  spotPrice: number
  perpPrice: number
  onSuccess?: () => void
}

export default function TradeForm({ symbol, spotPrice, perpPrice, onSuccess }: TradeFormProps) {
  const [notional, setNotional] = useState('')
  const [leverage, setLeverage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<{
    qty: number
    spotCost: number
    perpCost: number
    fees: number
  } | null>(null)

  const calculatePreview = () => {
    const notionalValue = parseFloat(notional)
    if (isNaN(notionalValue) || notionalValue <= 0) {
      setPreview(null)
      return
    }

    const qty = notionalValue / spotPrice
    const spotCost = notionalValue
    const perpCost = qty * perpPrice
    // Estimate fees (taker fees)
    const fees = (spotCost * 0.001) + (perpCost * 0.0004) // 0.1% spot + 0.04% perp

    setPreview({ qty, spotCost, perpCost, fees })
  }

  const handleNotionalChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setNotional(e.target.value)
    calculatePreview()
  }

  const handleOpenDeltaNeutral = async () => {
    if (!notional || parseFloat(notional) <= 0) {
      setError('Invalid notional amount')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await api.openDeltaNeutral({
        symbol,
        notional: parseFloat(notional),
        leverage,
      })
      onSuccess?.()
      setNotional('')
      setPreview(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open position')
    } finally {
      setLoading(false)
    }
  }

  const handleCloseDeltaNeutral = async () => {
    setLoading(true)
    setError(null)

    try {
      await api.closeDeltaNeutral({ symbol })
      onSuccess?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close position')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Trade Panel</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notional Amount (USDT)
          </label>
          <input
            type="number"
            value={notional}
            onChange={handleNotionalChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter amount in USDT"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Leverage (for perp)
          </label>
          <input
            type="number"
            value={leverage}
            onChange={(e) => setLeverage(parseInt(e.target.value) || 1)}
            min="1"
            max="10"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {preview && (
          <div className="bg-gray-50 p-4 rounded-md">
            <h4 className="font-medium mb-2">Preview</h4>
            <div className="space-y-1 text-sm">
              <div>Quantity: {preview.qty.toFixed(6)}</div>
              <div>Spot Cost: ${preview.spotCost.toFixed(2)}</div>
              <div>Perp Cost: ${preview.perpCost.toFixed(2)}</div>
              <div>Estimated Fees: ${preview.fees.toFixed(2)}</div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="flex space-x-3">
          <button
            onClick={handleOpenDeltaNeutral}
            disabled={loading || !notional}
            className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
          >
            {loading ? 'Processing...' : 'Open Delta-Neutral'}
          </button>
          <button
            onClick={handleCloseDeltaNeutral}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-400"
          >
            {loading ? 'Processing...' : 'Close Delta-Neutral'}
          </button>
        </div>
      </div>
    </div>
  )
}

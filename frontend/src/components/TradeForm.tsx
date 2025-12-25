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
    <div className="bg-black/50 border border-green-500/30 p-6 rounded-lg shadow-lg shadow-green-500/20">
      <h3 className="text-xl font-bold mb-4 text-green-400 text-glow">💰 Trade Panel</h3>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-green-400 mb-1 text-glow">
            Notional Amount (USDT)
          </label>
          <input
            type="number"
            value={notional}
            onChange={handleNotionalChange}
            className="w-full px-3 py-2 bg-black border border-green-500/50 text-green-400 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
            placeholder="Enter amount in USDT"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-green-400 mb-1 text-glow">
            Leverage (for perp)
          </label>
          <input
            type="number"
            value={leverage}
            onChange={(e) => setLeverage(parseInt(e.target.value) || 1)}
            min="1"
            max="10"
            className="w-full px-3 py-2 bg-black border border-green-500/50 text-green-400 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 font-mono"
          />
        </div>

        {preview && (
          <div className="bg-green-900/20 border border-green-500/30 p-4 rounded-md animate-bounce-in">
            <h4 className="font-bold mb-2 text-green-400 text-glow">📊 Preview</h4>
            <div className="space-y-1 text-sm text-green-300 font-mono">
              <div className="animate-slide-up">Quantity: <span className="text-green-400 font-bold">{preview.qty.toFixed(6)}</span></div>
              <div className="animate-slide-up" style={{ animationDelay: '0.1s' }}>Spot Cost: <span className="text-green-400 font-bold animate-number-flash">${preview.spotCost.toFixed(2)}</span></div>
              <div className="animate-slide-up" style={{ animationDelay: '0.2s' }}>Perp Cost: <span className="text-green-400 font-bold animate-number-flash">${preview.perpCost.toFixed(2)}</span></div>
              <div className="animate-slide-up" style={{ animationDelay: '0.3s' }}>Estimated Fees: <span className="text-yellow-400 font-bold">${preview.fees.toFixed(2)}</span></div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-900/30 border border-red-500/50 text-red-400 px-4 py-3 rounded text-glow animate-pulse-glow">
            ⚠️ {error}
          </div>
        )}

        <div className="flex space-x-3">
          <button
            onClick={handleOpenDeltaNeutral}
            disabled={loading || !notional}
            className="flex-1 px-4 py-2 bg-green-600 text-black font-bold rounded hover:bg-green-500 disabled:bg-gray-600 disabled:text-gray-400 hover-glow transition-all animate-bounce-in"
          >
            {loading ? '⚡ Processing...' : '🚀 Open Delta-Neutral'}
          </button>
          <button
            onClick={handleCloseDeltaNeutral}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-red-600 text-white font-bold rounded hover:bg-red-500 disabled:bg-gray-600 disabled:text-gray-400 hover-glow transition-all animate-bounce-in"
          >
            {loading ? '⚡ Processing...' : '🛑 Close Delta-Neutral'}
          </button>
        </div>
      </div>
    </div>
  )
}

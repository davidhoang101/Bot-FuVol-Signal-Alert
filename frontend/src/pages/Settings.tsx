import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Settings() {
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [paperMode, setPaperMode] = useState(false)

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true)
        const data = await api.getConfig()
        setConfig(data)
        setPaperMode(data.trading?.paper_mode || false)
      } catch (err) {
        console.error('Failed to fetch config:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  if (loading) {
    return <div className="text-center py-8">Loading settings...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Trading Configuration</h2>

        <div className="space-y-4">
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={paperMode}
                onChange={(e) => setPaperMode(e.target.checked)}
                className="mr-2"
                disabled
              />
              <span className="text-sm text-gray-700">
                Paper Mode (Dry Run) - {paperMode ? 'Enabled' : 'Disabled'}
              </span>
            </label>
            <p className="text-xs text-gray-500 mt-1">
              Paper mode is controlled by config.yaml. Changes require server restart.
            </p>
          </div>

          {config && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <div className="text-sm font-medium text-gray-700">Max Notional per Symbol</div>
                <div className="text-lg">${config.trading?.max_notional_per_symbol || 0}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-700">Max Total Notional</div>
                <div className="text-lg">${config.trading?.max_total_notional || 0}</div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-700">Min Free Margin %</div>
                <div className="text-lg">{config.trading?.min_free_margin_pct || 0}%</div>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-700">Default Leverage</div>
                <div className="text-lg">{config.trading?.default_leverage || 1}x</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Binance Configuration</h2>

        <div className="space-y-2 text-sm">
          <div>
            <span className="text-gray-600">API Key: </span>
            <span className="font-mono text-gray-400">•••••••• (hidden)</span>
          </div>
          <div>
            <span className="text-gray-600">Testnet: </span>
            <span>{config?.binance?.testnet ? 'Enabled' : 'Disabled'}</span>
          </div>
        </div>

        <p className="text-xs text-gray-500 mt-4">
          API credentials are stored in .env file. Changes require server restart.
        </p>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-4">Funding Scanner Configuration</h2>

        {config && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm font-medium text-gray-700">Min Rate</div>
              <div className="text-lg">{config.funding_scanner?.min_rate || 0}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-700">Max Spread (bps)</div>
              <div className="text-lg">{config.funding_scanner?.max_spread_bps || 0}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-700">Refresh (sec)</div>
              <div className="text-lg">{config.funding_scanner?.refresh_sec || 0}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

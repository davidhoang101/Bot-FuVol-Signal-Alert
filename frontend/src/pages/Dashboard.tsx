import { useState } from 'react'
import FundingTable from '../components/FundingTable'

export default function Dashboard() {
  const [minRate, setMinRate] = useState<number | undefined>(0.0002)
  const [maxSpreadBps, setMaxSpreadBps] = useState<number | undefined>(8)
  const [autoRefresh, setAutoRefresh] = useState(false)

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-4">Funding Rate Scanner</h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Min Funding Rate
            </label>
            <input
              type="number"
              step="0.0001"
              value={minRate || ''}
              onChange={(e) => setMinRate(e.target.value ? parseFloat(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="0.0002"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Spread (bps)
            </label>
            <input
              type="number"
              step="0.1"
              value={maxSpreadBps || ''}
              onChange={(e) => setMaxSpreadBps(e.target.value ? parseFloat(e.target.value) : undefined)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="8"
            />
          </div>

          <div className="flex items-end">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">Auto Refresh</span>
            </label>
          </div>
        </div>
      </div>

      <FundingTable
        minRate={minRate}
        maxSpreadBps={maxSpreadBps}
        autoRefresh={autoRefresh}
        refreshInterval={10000}
      />
    </div>
  )
}

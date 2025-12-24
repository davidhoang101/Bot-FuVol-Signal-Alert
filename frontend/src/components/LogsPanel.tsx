import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

interface LogEntry {
  id: number
  timestamp: string
  level: string
  message: string
  context: any
}

export default function LogsPanel() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const response = await api.getLogs({ limit: 50 })
      setLogs(response.logs || [])
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 2000) // Poll every 2 seconds
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'text-red-600'
      case 'warning':
        return 'text-yellow-600'
      case 'info':
        return 'text-blue-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Event Logs</h3>
        <button
          onClick={fetchLogs}
          className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
        >
          Refresh
        </button>
      </div>

      <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm h-64 overflow-y-auto">
        {loading && logs.length === 0 ? (
          <div className="text-center py-8">Loading logs...</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No logs yet</div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="mb-2">
              <span className="text-gray-500">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`ml-2 ${getLevelColor(log.level)}`}>
                [{log.level.toUpperCase()}]
              </span>
              <span className="ml-2">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}

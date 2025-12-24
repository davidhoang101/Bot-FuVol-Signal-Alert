import { useState, useEffect } from 'react'
import { api } from '../api/client'

interface Order {
  id: number
  symbol: string
  market_type: string
  side: string
  order_type: string
  qty: number
  price: number | null
  status: string
  exchange_order_id: string | null
  fill_price: number | null
  fill_qty: number | null
  created_at: string
}

export default function OrdersTable({ symbol }: { symbol?: string }) {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)

  const fetchOrders = async () => {
    try {
      setLoading(true)
      const response = await api.getOrders({ symbol })
      setOrders(response.orders || [])
    } catch (err) {
      console.error('Failed to fetch orders:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
    const interval = setInterval(fetchOrders, 3000) // Poll every 3 seconds
    return () => clearInterval(interval)
  }, [symbol])

  if (loading && orders.length === 0) {
    return <div className="text-center py-4">Loading orders...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Open Orders</h3>
        <button
          onClick={fetchOrders}
          className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
        >
          Refresh
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Market</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Side</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {orders.map((order) => (
              <tr key={order.id}>
                <td className="px-4 py-2 text-sm">{order.symbol}</td>
                <td className="px-4 py-2 text-sm">{order.market_type}</td>
                <td className="px-4 py-2 text-sm">{order.side}</td>
                <td className="px-4 py-2 text-sm">{order.qty.toFixed(6)}</td>
                <td className="px-4 py-2 text-sm">{order.price?.toFixed(4) || 'Market'}</td>
                <td className="px-4 py-2 text-sm">
                  <span className={`px-2 py-1 rounded text-xs ${
                    order.status === 'filled' ? 'bg-green-100 text-green-800' :
                    order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                    order.status === 'simulated' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {order.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-sm text-gray-500">
                  {new Date(order.created_at).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {orders.length === 0 && (
          <div className="text-center py-8 text-gray-500">No orders found</div>
        )}
      </div>
    </div>
  )
}

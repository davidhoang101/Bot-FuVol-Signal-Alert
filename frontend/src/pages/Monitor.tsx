import OrdersTable from '../components/OrdersTable'
import PositionsCard from '../components/PositionsCard'
import MarginCard from '../components/MarginCard'
import LogsPanel from '../components/LogsPanel'

export default function Monitor() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Monitor</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MarginCard />
        <PositionsCard />
      </div>

      <OrdersTable />

      <LogsPanel />
    </div>
  )
}

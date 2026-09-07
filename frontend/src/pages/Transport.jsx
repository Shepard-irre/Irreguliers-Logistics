import { useEffect, useState } from 'react'
import Topbar from '../components/Topbar'
import Tabs from '../components/Tabs'
import { getTransportOrders, takeTransportOrder, deliverTransportOrder } from '../lib/api'

const TABS = [
  { key: 'pending', label: 'Bons en attente' },
  { key: 'in_progress', label: 'En cours' },
  { key: 'delivered', label: 'Livrés' },
]

function qualityDot(q) {
  if (q >= 700) return 'bg-irr-green'
  if (q >= 400) return 'bg-irr-amber'
  return 'bg-red-500'
}

export default function Transport() {
  const [activeTab, setActiveTab] = useState('pending')
  const [orders, setOrders] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    try {
      setOrders(await getTransportOrders(activeTab))
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    setOrders(null)
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  async function handleTake(orderId) {
    await takeTransportOrder(orderId)
    await load()
  }

  async function handleDeliver(orderId) {
    await deliverTransportOrder(orderId)
    await load()
  }

  return (
    <>
      <Topbar title="TRANSPORT" subtitle={TABS.find((t) => t.key === activeTab)?.label} />

      <div className="px-8 pt-5">
        <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />
      </div>

      <div className="flex-1 p-8 flex flex-col gap-4">
        {error && <div className="text-red-400 text-sm">{error}</div>}
        {orders === null && !error && <div className="text-irr-dim text-sm">Chargement…</div>}
        {orders && orders.length === 0 && <div className="text-irr-dim text-sm">Aucun bon.</div>}

        {(orders || []).map((order) => (
          <div key={order.id} className="cut bg-irr-panel border border-irr-border p-5 flex flex-col gap-3">
            <div className="flex justify-between items-start">
              <div className="flex flex-col gap-1">
                <span className="font-display font-bold text-base tracking-wide">{order.commodity_name}</span>
                <span className="text-xs text-irr-dim">{order.quantity} SCU</span>
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs">
                <span className={`w-2 h-2 rounded-full ${qualityDot(order.quality)}`} />
                Q{order.quality}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><span className="text-irr-dim">Pickup :</span> {order.pickup_location}</div>
              <div><span className="text-irr-dim">Livraison :</span> {order.delivery_location}</div>
              <div><span className="text-irr-dim">Assigné à :</span> {order.assigned_to}</div>
              <div><span className="text-irr-dim">Émis par :</span> {order.created_by}</div>
            </div>

            {order.notes && <div className="text-xs text-irr-muted">Notes : {order.notes}</div>}
            <div className="text-[10px] text-irr-dim font-mono">{order.date_created}</div>

            {activeTab === 'pending' && (
              <button
                onClick={() => handleTake(order.id)}
                className="cut-sm self-start bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide px-4 py-2"
              >
                Prendre en charge
              </button>
            )}
            {activeTab === 'in_progress' && (
              <button
                onClick={() => handleDeliver(order.id)}
                className="cut-sm self-start bg-irr-green-dim border border-irr-green text-irr-green font-display font-semibold text-sm tracking-wide px-4 py-2"
              >
                Confirmer la livraison
              </button>
            )}
          </div>
        ))}
      </div>
    </>
  )
}

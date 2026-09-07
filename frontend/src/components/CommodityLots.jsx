import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getRaffineriesLots, toggleRaffineryLotBlocked } from '../lib/api'

function qualityDot(q) {
  if (q >= 700) return 'bg-irr-green'
  if (q >= 400) return 'bg-irr-amber'
  return 'bg-red-500'
}

export default function CommodityLots() {
  const { user } = useAuth()
  const canBlock = user?.permissions?.includes('page_gestion_stock')
  const [lots, setLots] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    try {
      setLots(await getRaffineriesLots())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleToggle(lotId, isBlocked) {
    await toggleRaffineryLotBlocked(lotId, !isBlocked)
    await load()
  }

  return (
    <div className="flex flex-col gap-3">
      <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">
        Minerais en stock
      </span>
      {error && <div className="text-red-400 text-sm">{error}</div>}
      {lots === null && !error && <div className="text-irr-dim text-sm">Chargement…</div>}
      {lots && lots.length === 0 && <div className="text-irr-dim text-sm">Aucun minerai en stock.</div>}
      {lots && lots.length > 0 && (
        <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                <th className="text-left px-4 py-2.5">Minerai</th>
                <th className="text-right px-4 py-2.5">SCU</th>
                <th className="text-right px-4 py-2.5">Qualité</th>
                <th className="text-left px-4 py-2.5">Statut</th>
                {canBlock && <th className="text-right px-4 py-2.5">Action</th>}
              </tr>
            </thead>
            <tbody>
              {lots.map((lot) => (
                <tr key={lot.id} className="border-b border-irr-border last:border-0">
                  <td className="px-4 py-2">{lot.Minerai}</td>
                  <td className="px-4 py-2 text-right font-mono">{lot.SCU}</td>
                  <td className="px-4 py-2 text-right">
                    <span className="inline-flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${qualityDot(lot.Qualité)}`} />
                      {lot.Qualité}/1000
                    </span>
                  </td>
                  <td className="px-4 py-2 text-irr-muted">
                    {lot.Bloqué ? `🔒 ${lot['Bloqué par'] || 'Réservé'}` : '✅ Disponible'}
                  </td>
                  {canBlock && (
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => handleToggle(lot.id, lot.Bloqué)}
                        className="text-xs font-display font-semibold text-irr-dim hover:text-irr-text"
                      >
                        {lot.Bloqué ? 'Débloquer' : 'Bloquer'}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

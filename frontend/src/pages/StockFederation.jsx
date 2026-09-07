import { useEffect, useState } from 'react'
import Topbar from '../components/Topbar'
import { getFedStockSummary, getFedInventory, getFedLots, getFedLogs } from '../lib/api'

export default function StockFederation() {
  const [summary, setSummary] = useState(null)
  const [inventory, setInventory] = useState(null)
  const [lots, setLots] = useState(null)
  const [logs, setLogs] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([getFedStockSummary(), getFedInventory(), getFedLots(), getFedLogs()])
      .then(([s, inv, l, log]) => {
        setSummary(s)
        setInventory(inv)
        setLots(l)
        setLogs(log)
      })
      .catch((e) => setError(e.message))
  }, [])

  function qualityDot(q) {
    if (q >= 700) return 'bg-irr-green'
    if (q >= 400) return 'bg-irr-amber'
    return 'bg-red-500'
  }

  return (
    <>
      <Topbar title="STOCK FÉDÉRATION" subtitle="État des stocks & historique" />

      <div className="flex-1 p-8 flex flex-col gap-6">
        {error && <div className="text-red-400 text-sm">{error}</div>}

        <div className="grid grid-cols-3 gap-4">
          <StatTile label="Composants en stock" value={summary ? summary.total_components.toLocaleString('fr-FR') : '—'} />
          <StatTile label="Minerais en stock (SCU)" value={summary ? summary.total_minerals.toLocaleString('fr-FR') : '—'} />
          <StatTile label="Solde Fédération" value={summary ? `${summary.fed_balance.toLocaleString('fr-FR')} aUEC` : '—'} accent />
        </div>

        <div className="grid grid-cols-5 gap-6">
          <div className="col-span-3 flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">Composants</span>
              {inventory === null && <div className="text-irr-dim text-sm">Chargement…</div>}
              {inventory && inventory.length === 0 && <div className="text-irr-dim text-sm">Aucun composant en stock.</div>}
              {inventory && inventory.length > 0 && (
                <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                        <th className="text-left px-4 py-2.5">Nom</th>
                        <th className="text-left px-4 py-2.5">Catégorie</th>
                        <th className="text-right px-4 py-2.5">Quantité</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inventory.map((item) => (
                        <tr key={item.item_id} className="border-b border-irr-border last:border-0">
                          <td className="px-4 py-2">{item.Nom}</td>
                          <td className="px-4 py-2 text-irr-muted">{item.Type}</td>
                          <td className="px-4 py-2 text-right font-mono">{item.Qté}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">Minerais</span>
              {lots === null && <div className="text-irr-dim text-sm">Chargement…</div>}
              {lots && lots.length === 0 && <div className="text-irr-dim text-sm">Aucun minerai en stock.</div>}
              {lots && lots.length > 0 && (
                <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                        <th className="text-left px-4 py-2.5">Minerai</th>
                        <th className="text-right px-4 py-2.5">SCU</th>
                        <th className="text-right px-4 py-2.5">Qualité</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lots.map((lot, i) => (
                        <tr key={i} className="border-b border-irr-border last:border-0">
                          <td className="px-4 py-2">{lot.Minerai}</td>
                          <td className="px-4 py-2 text-right font-mono">{lot.SCU}</td>
                          <td className="px-4 py-2 text-right">
                            <span className="inline-flex items-center gap-1.5">
                              <span className={`w-2 h-2 rounded-full ${qualityDot(lot.Qualité)}`} />
                              {lot.Qualité}/1000
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="col-span-2 flex flex-col gap-2">
            <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">Activité des entrées</span>
            {logs === null && <div className="text-irr-dim text-sm">Chargement…</div>}
            {logs && (
              <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
                <table className="w-full text-xs">
                  <tbody>
                    {logs.map((log, i) => (
                      <tr key={i} className="border-b border-irr-border last:border-0">
                        <td className="px-3 py-2 text-irr-dim font-mono whitespace-nowrap">{log.Date}</td>
                        <td className="px-3 py-2">{log.Pilote}</td>
                        <td className="px-3 py-2 text-irr-muted">{log.Action}</td>
                        <td className="px-3 py-2 text-right font-mono">{log.Qté}</td>
                        <td className="px-3 py-2">{log.Article}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function StatTile({ label, value, accent }) {
  return (
    <div className="cut bg-irr-panel border border-irr-border p-4 flex flex-col gap-1.5">
      <span className="text-[11px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">{label}</span>
      <span className={`font-mono font-semibold text-2xl ${accent ? 'text-irr-accent' : 'text-irr-text'}`}>{value}</span>
    </div>
  )
}

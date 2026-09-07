import { useEffect, useMemo, useState } from 'react'
import Topbar from '../components/Topbar'
import { getCommodities, getCommodityPrices } from '../lib/api'

function formatContainers(sizesStr) {
  if (!sizesStr) return '?'
  const sizes = String(sizesStr).split(',').map((s) => parseInt(s, 10)).filter((n) => !Number.isNaN(n))
  return sizes.length ? `1–${Math.max(...sizes)} SCU` : '?'
}

export default function Commerce() {
  const [commodities, setCommodities] = useState(null)
  const [commodityId, setCommodityId] = useState('')
  const [volume, setVolume] = useState(32)
  const [buyers, setBuyers] = useState(null)
  const [system, setSystem] = useState('Tous')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getCommodities()
      .then((list) => {
        setCommodities(list)
        if (list.length) setCommodityId(String(list[0].id))
      })
      .catch((e) => setError(e.message))
  }, [])

  async function handleSearch() {
    setBusy(true)
    setError(null)
    try {
      const result = await getCommodityPrices(Number(commodityId))
      setBuyers(result.sort((a, b) => b.price_sell - a.price_sell))
      setSystem('Tous')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const systems = useMemo(() => {
    if (!buyers) return []
    return [...new Set(buyers.map((b) => b.star_system_name).filter(Boolean))].sort()
  }, [buyers])

  const filtered = useMemo(() => {
    if (!buyers) return []
    return system === 'Tous' ? buyers : buyers.filter((b) => b.star_system_name === system)
  }, [buyers, system])

  const bestPrice = filtered[0]?.price_sell || 0

  return (
    <>
      <Topbar title="COMMERCE" subtitle="Marché public" />

      <div className="flex-1 p-8 flex flex-col gap-6">
        <div className="cut bg-irr-panel border border-irr-border p-5 flex items-end gap-4">
            <label className="flex flex-col gap-1 flex-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Ressource
              </span>
              <select
                value={commodityId}
                onChange={(e) => setCommodityId(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
              >
                {(commodities || []).map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Volume (SCU)
              </span>
              <input
                type="number"
                min="1"
                value={volume}
                onChange={(e) => setVolume(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 font-mono text-sm text-irr-text w-28 focus:outline-none focus:border-irr-accent"
              />
            </label>
            <button
              onClick={handleSearch}
              disabled={busy || !commodityId}
              className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide px-5 py-2.5 disabled:opacity-50"
            >
              Calculer les points de vente
            </button>
          </div>

          {error && <div className="text-red-400 text-sm">{error}</div>}

          {buyers && (
            filtered.length === 0 ? (
              <div className="text-irr-dim text-sm">Aucun acheteur dans ce système.</div>
            ) : (
              <>
                <div className="cut bg-irr-panel border border-irr-border p-4 flex flex-col gap-1.5 w-fit">
                  <span className="text-[11px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                    Valeur marché max ({volume} SCU)
                  </span>
                  <span className="font-mono font-semibold text-2xl text-irr-accent">
                    {(bestPrice * volume).toLocaleString('fr-FR')} aUEC
                  </span>
                </div>

                <div className="flex gap-2 flex-wrap">
                  {['Tous', ...systems].map((s) => (
                    <button
                      key={s}
                      onClick={() => setSystem(s)}
                      className={`cut-sm px-3 py-1.5 text-xs font-display font-semibold tracking-wide border ${
                        system === s
                          ? 'bg-irr-accent-dim border-irr-accent text-irr-accent'
                          : 'border-irr-border-strong text-irr-muted'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>

                <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                        <th className="text-left px-4 py-3">Terminal</th>
                        <th className="text-right px-4 py-3">Prix/SCU</th>
                        <th className="text-left px-4 py-3">Système</th>
                        <th className="text-left px-4 py-3">Caisses</th>
                        <th className="text-right px-4 py-3">Qté présente</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((b, i) => (
                        <tr key={i} className="border-b border-irr-border last:border-0">
                          <td className="px-4 py-2.5">{b.terminal_name}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-irr-accent">{b.price_sell.toLocaleString('fr-FR')}</td>
                          <td className="px-4 py-2.5 text-irr-muted">{b.star_system_name}</td>
                          <td className="px-4 py-2.5 text-irr-muted">{formatContainers(b.container_sizes)}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-irr-muted">
                            {b.scu_sell_stock ? `${Math.round(b.scu_sell_stock)} SCU` : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )
          )}
        </div>
    </>
  )
}

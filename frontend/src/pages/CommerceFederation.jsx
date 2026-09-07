import { useEffect, useState } from 'react'
import Topbar from '../components/Topbar'
import { getFedPrices, setFedPrice, getBestMarketPrice } from '../lib/api'

export default function CommerceFederation() {
  const [rows, setRows] = useState(null)
  const [commodityId, setCommodityId] = useState('')
  const [newPrice, setNewPrice] = useState(0)
  const [bestPrice, setBestPrice] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    try {
      const list = await getFedPrices()
      setRows(list)
      if (list.length && !commodityId) setCommodityId(String(list[0].commodity_id))
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const row = rows?.find((r) => String(r.commodity_id) === commodityId)
    if (row) setNewPrice(row.price_fed)
    setBestPrice(null)
  }, [commodityId, rows])

  async function handleCompare() {
    try {
      const result = await getBestMarketPrice(Number(commodityId))
      setBestPrice(result.price_sell)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleUpdate() {
    try {
      await setFedPrice(Number(commodityId), Number(newPrice))
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <>
      <Topbar title="COMMERCE FÉDÉRATION" subtitle="Pilotage commercial" />

      <div className="flex-1 p-8 flex flex-col gap-6">
        <div className="cut bg-irr-panel border border-irr-border p-5 flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <label className="flex flex-col gap-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Ressource à réguler
              </span>
              <select
                value={commodityId}
                onChange={(e) => setCommodityId(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
              >
                {(rows || []).map((r) => (
                  <option key={r.commodity_id} value={r.commodity_id}>{r.name}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Prix d'achat Fédération
              </span>
              <input
                type="number"
                min="0"
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 font-mono text-sm text-irr-text focus:outline-none focus:border-irr-accent"
              />
            </label>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleCompare}
              className="cut-sm border border-irr-border-strong text-irr-muted font-display font-semibold text-sm tracking-wide px-4 py-2"
            >
              Comparer au meilleur cours
            </button>
            <button
              onClick={handleUpdate}
              className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide px-5 py-2"
            >
              Mettre à jour le tarif Fed
            </button>
          </div>

          {bestPrice !== null && (
            <div className="text-sm text-irr-accent">Référence marché : {bestPrice.toLocaleString('fr-FR')} aUEC / SCU</div>
          )}
        </div>

        {error && <div className="text-red-400 text-sm">{error}</div>}

        <div className="flex flex-col gap-2">
          <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">Grille tarifaire interne</span>
          {rows === null && <div className="text-irr-dim text-sm">Chargement…</div>}
          {rows && (
            <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                    <th className="text-left px-4 py-3">Ressource</th>
                    <th className="text-right px-4 py-3">Prix Fédération</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.filter((r) => r.price_fed > 0).map((r) => (
                    <tr key={r.commodity_id} className="border-b border-irr-border last:border-0">
                      <td className="px-4 py-2.5">{r.name}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-irr-accent">{r.price_fed.toLocaleString('fr-FR')} aUEC</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

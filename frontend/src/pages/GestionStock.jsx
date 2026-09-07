import { useEffect, useMemo, useState } from 'react'
import Topbar from '../components/Topbar'
import {
  getStockCategories,
  getStockItems,
  getItemPrices,
  addToStock,
  getInventory,
  setItemVisibility,
  getStockLogs,
} from '../lib/api'

export default function GestionStock() {
  const [categories, setCategories] = useState(null)
  const [categoryLabel, setCategoryLabel] = useState('')
  const [items, setItems] = useState([])
  const [itemLabel, setItemLabel] = useState('')
  const [prices, setPrices] = useState(null)
  const [quantity, setQuantity] = useState(1)
  const [inventory, setInventory] = useState(null)
  const [logs, setLogs] = useState(null)
  const [showVisibility, setShowVisibility] = useState(false)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    getStockCategories()
      .then((cats) => {
        setCategories(cats)
        if (cats.length) setCategoryLabel(cats[0].label)
      })
      .catch((e) => setError(e.message))
    loadInventory()
    loadLogs()
  }, [])

  useEffect(() => {
    if (!categories || !categoryLabel) return
    const cat = categories.find((c) => c.label === categoryLabel)
    if (!cat) return
    getStockItems(cat.category_ids)
      .then((list) => {
        setItems(list)
        setItemLabel(list[0] ? itemKey(list[0]) : '')
        setPrices(null)
      })
      .catch((e) => setError(e.message))
  }, [categories, categoryLabel])

  function itemKey(item) {
    return `${item.name} (S${item.size ?? '?'})`
  }

  async function loadInventory() {
    try {
      setInventory(await getInventory())
    } catch (e) {
      setError(e.message)
    }
  }

  async function loadLogs() {
    try {
      setLogs(await getStockLogs())
    } catch (e) {
      setError(e.message)
    }
  }

  const selectedItem = useMemo(() => items.find((i) => itemKey(i) === itemLabel), [items, itemLabel])

  async function handleShowPrices() {
    if (!selectedItem) return
    try {
      setPrices(await getItemPrices(selectedItem.id))
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleAddStock() {
    if (!selectedItem) return
    try {
      await addToStock({
        item_id: selectedItem.id,
        name: selectedItem.name,
        category: categoryLabel,
        size: String(selectedItem.size ?? '?'),
        quantity: Number(quantity),
      })
      setToast('Inventaire mis à jour.')
      await loadInventory()
      await loadLogs()
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleToggleHidden(item) {
    await setItemVisibility(item.item_id, !item.Caché)
    await loadInventory()
  }

  return (
    <>
      <Topbar title="GESTION DE STOCK" subtitle="Fédération" />

      <div className="flex-1 p-8 flex flex-col gap-6">
        <div className="cut bg-irr-panel border border-irr-border p-5 flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <label className="flex flex-col gap-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Catégorie
              </span>
              <select
                value={categoryLabel}
                onChange={(e) => setCategoryLabel(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
              >
                {(categories || []).map((c) => (
                  <option key={c.label} value={c.label}>{c.label}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Modèle
              </span>
              <select
                value={itemLabel}
                onChange={(e) => setItemLabel(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
              >
                {items.map((i) => (
                  <option key={itemKey(i)} value={itemKey(i)}>{itemKey(i)}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="flex items-end gap-4">
            <button
              onClick={handleShowPrices}
              className="cut-sm border border-irr-border-strong text-irr-muted font-display font-semibold text-sm tracking-wide px-4 py-2"
            >
              Prix UEX
            </button>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                Quantité trouvée
              </span>
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 font-mono text-sm text-irr-text w-24 focus:outline-none focus:border-irr-accent"
              />
            </label>
            <button
              onClick={handleAddStock}
              className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide px-5 py-2"
            >
              Ajouter au stock
            </button>
          </div>

          {toast && <div className="text-irr-accent text-xs">{toast}</div>}

          {prices && (
            <div className="cut-sm bg-irr-panel-alt border border-irr-border overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                    <th className="text-left px-3 py-2">Terminal</th>
                    <th className="text-right px-3 py-2">Prix achat</th>
                    <th className="text-left px-3 py-2">Système</th>
                  </tr>
                </thead>
                <tbody>
                  {[...prices].sort((a, b) => a.price_buy - b.price_buy).map((p, i) => (
                    <tr key={i} className="border-b border-irr-border last:border-0">
                      <td className="px-3 py-2">{p.terminal_name}</td>
                      <td className="px-3 py-2 text-right font-mono">{p.price_buy?.toLocaleString('fr-FR')}</td>
                      <td className="px-3 py-2 text-irr-muted">{p.star_system_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {error && <div className="text-red-400 text-sm">{error}</div>}

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">
              Composants en stock
            </span>
            <button
              onClick={() => setShowVisibility((v) => !v)}
              className="text-irr-dim hover:text-irr-text text-xs font-display font-semibold"
            >
              {showVisibility ? 'Fermer' : 'Gérer la visibilité'}
            </button>
          </div>

          {inventory === null && <div className="text-irr-dim text-sm">Chargement…</div>}
          {inventory && inventory.length === 0 && <div className="text-irr-dim text-sm">Aucun composant en stock.</div>}

          {inventory && inventory.length > 0 && (
            <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                    <th className="text-left px-4 py-3">Nom</th>
                    <th className="text-left px-4 py-3">Catégorie</th>
                    <th className="text-right px-4 py-3">Disponible</th>
                    {showVisibility && <th className="text-right px-4 py-3">Visibilité</th>}
                  </tr>
                </thead>
                <tbody>
                  {inventory.map((item) => (
                    <tr key={item.item_id} className="border-b border-irr-border last:border-0">
                      <td className="px-4 py-2.5">{item.Nom}</td>
                      <td className="px-4 py-2.5 text-irr-muted">{item.Type}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{item.Qté}</td>
                      {showVisibility && (
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() => handleToggleHidden(item)}
                            className="text-xs font-display font-semibold text-irr-muted hover:text-irr-text"
                          >
                            {item.Caché ? 'Caché — rendre visible' : 'Visible — masquer'}
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

        <div className="flex flex-col gap-3">
          <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">
            Activité des entrées
          </span>
          {logs === null && <div className="text-irr-dim text-sm">Chargement…</div>}
          {logs && (
            <div className="cut bg-irr-panel border border-irr-border overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                    <th className="text-left px-4 py-3">Date</th>
                    <th className="text-left px-4 py-3">Pilote</th>
                    <th className="text-left px-4 py-3">Action</th>
                    <th className="text-right px-4 py-3">Qté</th>
                    <th className="text-left px-4 py-3">Article</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, i) => (
                    <tr key={i} className="border-b border-irr-border last:border-0">
                      <td className="px-4 py-2.5 text-irr-muted font-mono text-xs">{log.Date}</td>
                      <td className="px-4 py-2.5">{log.Pilote}</td>
                      <td className="px-4 py-2.5 text-irr-muted">{log.Action}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{log.Qté}</td>
                      <td className="px-4 py-2.5">{log.Article}</td>
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

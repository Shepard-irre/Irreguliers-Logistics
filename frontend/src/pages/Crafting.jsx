import { useState } from 'react'
import Topbar from '../components/Topbar'
import Tabs from '../components/Tabs'
import { useAuth } from '../context/AuthContext'
import {
  searchBlueprints,
  getLotsForIngredient,
  toggleLotBlocked,
  getBlockedLots,
} from '../lib/api'
import { useEffect } from 'react'

const TABS = [
  { key: 'search', label: 'Rechercher un blueprint' },
  { key: 'reserved', label: 'Lots réservés' },
]

function formatCraftTime(seconds) {
  if (!seconds) return '0s'
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}min`
  if (seconds >= 60) return `${Math.floor(seconds / 60)}min ${seconds % 60}s`
  return `${seconds}s`
}

function qualityDot(q) {
  if (q >= 700) return 'bg-irr-green'
  if (q >= 400) return 'bg-irr-amber'
  return 'bg-red-500'
}

const BADGE_CLASSES = {
  ok: 'bg-irr-green-dim border-irr-green text-irr-green',
  partial: 'bg-irr-amber-dim border-irr-amber text-irr-amber',
  missing: 'border-red-500 text-red-400',
}

export default function Crafting() {
  const [activeTab, setActiveTab] = useState('search')

  return (
    <>
      <Topbar title="CRAFTING" subtitle={TABS.find((t) => t.key === activeTab)?.label} />
      <div className="px-8 pt-5">
        <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />
      </div>
      <div className="flex-1 p-8 flex flex-col gap-4">
        {activeTab === 'search' ? <SearchTab /> : <ReservedTab />}
      </div>
    </>
  )
}

function SearchTab() {
  const { user } = useAuth()
  const canBlock = user?.permissions?.includes('crafting_stock_view')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)

  async function handleSearch() {
    if (!query.trim()) return
    try {
      const data = await searchBlueprints(query.trim())
      setResults(data.items || [])
      setTotal(data.pagination?.total || 0)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Sniper, Shield, Quantum Drive, Armor..."
          className="flex-1 bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
        />
        <button
          onClick={handleSearch}
          className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide px-5 py-2"
        >
          Rechercher
        </button>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}
      {results === null && <div className="text-irr-dim text-sm">Entre un terme de recherche pour trouver des blueprints.</div>}
      {results && results.length === 0 && <div className="text-irr-dim text-sm">Aucun blueprint trouvé.</div>}
      {results && results.length > 0 && (
        <div className="text-xs text-irr-dim">{total} résultat(s) — affichage des {results.length} premiers</div>
      )}

      <div className="flex flex-col gap-3">
        {(results || []).map((bp) => (
          <BlueprintCard
            key={bp.id}
            bp={bp}
            canBlock={canBlock}
            isOpen={expanded === bp.id}
            onToggle={() => setExpanded(expanded === bp.id ? null : bp.id)}
          />
        ))}
      </div>
    </div>
  )
}

function BlueprintCard({ bp, canBlock, isOpen, onToggle }) {
  const ingredients = bp.ingredients || []
  const analysis = bp.stock_analysis
  const [lotsByIngredient, setLotsByIngredient] = useState({})

  useEffect(() => {
    if (!isOpen || !canBlock) return
    ingredients.forEach((ing) => {
      getLotsForIngredient(ing.name).then((lots) =>
        setLotsByIngredient((prev) => ({ ...prev, [ing.name]: lots })),
      )
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  async function handleToggle(lotId, isBlocked, ingName) {
    await toggleLotBlocked(lotId, !isBlocked)
    const lots = await getLotsForIngredient(ingName)
    setLotsByIngredient((prev) => ({ ...prev, [ingName]: lots }))
  }

  return (
    <div className="cut bg-irr-panel border border-irr-border flex flex-col">
      <button onClick={onToggle} className="flex items-center justify-between px-5 py-3.5 text-left">
        <div className="flex items-center gap-3">
          {analysis && (
            <span className={`cut-sm border text-[10px] font-display font-semibold px-2 py-0.5 uppercase ${BADGE_CLASSES[analysis.stock_badge]}`}>
              {analysis.stock_badge}
            </span>
          )}
          <span className="font-display font-bold text-sm tracking-wide">{bp.name}</span>
          <span className="text-xs text-irr-dim">{bp.category}</span>
        </div>
        <span className="text-xs text-irr-muted">
          ⏱ {formatCraftTime(bp.craft_time_seconds)} · {ingredients.length} ingrédient(s)
        </span>
      </button>

      {isOpen && (
        <div className="px-5 pb-5 border-t border-irr-border pt-4 flex flex-col gap-4">
          {ingredients.length === 0 ? (
            <div className="text-irr-dim text-sm">Aucun ingrédient renseigné.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-irr-border text-irr-dim text-[10px] font-display font-semibold tracking-[0.1em] uppercase">
                  <th className="text-left px-2 py-2">Slot</th>
                  <th className="text-left px-2 py-2">Matière</th>
                  <th className="text-right px-2 py-2">Requis (SCU)</th>
                  <th className="text-right px-2 py-2">Qualité min</th>
                  {analysis && <th className="text-right px-2 py-2">Stock</th>}
                </tr>
              </thead>
              <tbody>
                {ingredients.map((ing, i) => {
                  const row = analysis?.rows?.[i]
                  return (
                    <tr key={i} className="border-b border-irr-border last:border-0">
                      <td className="px-2 py-2 text-irr-muted">{ing.slot || '—'}</td>
                      <td className="px-2 py-2">{ing.name}</td>
                      <td className="px-2 py-2 text-right font-mono">{ing.quantity_scu}</td>
                      <td className="px-2 py-2 text-right font-mono text-irr-muted">{ing.min_quality || '—'}</td>
                      {analysis && (
                        <td className="px-2 py-2 text-right font-mono">
                          {row.status === 'ok' && <span className="text-irr-green">{row.available_ok} SCU</span>}
                          {row.status === 'insufficient_quality' && <span className="text-irr-amber">{row.available_ok} SCU (qualité)</span>}
                          {row.status === 'missing' && <span className="text-red-400">Manquant</span>}
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {canBlock && ingredients.map((ing) => {
            const lots = lotsByIngredient[ing.name]
            if (!lots || lots.length === 0) return null
            return (
              <div key={ing.name} className="flex flex-col gap-1.5">
                <span className="text-xs font-display font-semibold">
                  {ing.name} — requis : {ing.quantity_scu} SCU{ing.min_quality ? ` | qualité min : ${ing.min_quality}` : ''}
                </span>
                {lots.map((lot) => (
                  <div key={lot.id} className="flex items-center justify-between text-xs bg-irr-panel-alt border border-irr-border px-3 py-1.5">
                    <span className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${qualityDot(lot.Qualité)}`} />
                      Lot #{lot.id} — {lot.SCU} SCU
                      {lot.Bloqué ? ` — 🔒 ${lot['Bloqué par']}` : ''}
                    </span>
                    <button
                      onClick={() => handleToggle(lot.id, lot.Bloqué, ing.name)}
                      className="text-irr-dim hover:text-irr-text font-display font-semibold"
                    >
                      {lot.Bloqué ? 'Débloquer' : 'Bloquer'}
                    </button>
                  </div>
                ))}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ReservedTab() {
  const { user } = useAuth()
  const isAdmin = user?.permissions?.includes('admin_panel')
  const [lots, setLots] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    try {
      setLots(await getBlockedLots())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleUnblock(lotId) {
    await toggleLotBlocked(lotId, false)
    await load()
  }

  if (error) return <div className="text-red-400 text-sm">{error}</div>
  if (lots === null) return <div className="text-irr-dim text-sm">Chargement…</div>
  if (lots.length === 0) return <div className="text-irr-dim text-sm">Aucun lot bloqué pour le moment.</div>

  const byOwner = {}
  for (const lot of lots) {
    const owner = lot['Bloqué par'] || '—'
    byOwner[owner] = byOwner[owner] || []
    byOwner[owner].push(lot)
  }
  const totalScu = lots.reduce((sum, l) => sum + l.SCU, 0)

  return (
    <div className="flex flex-col gap-4">
      <div className="cut bg-irr-panel border border-irr-border p-4 flex flex-col gap-1 w-fit">
        <span className="text-[11px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">Total SCU bloqués</span>
        <span className="font-mono font-semibold text-2xl text-irr-accent">{totalScu.toFixed(2)} SCU</span>
      </div>

      {Object.entries(byOwner).map(([owner, ownerLots]) => (
        <div key={owner} className="cut bg-irr-panel border border-irr-border p-4 flex flex-col gap-2">
          <span className="font-display font-bold text-sm">
            🔒 {owner} — {ownerLots.length} lot(s) | {ownerLots.reduce((s, l) => s + l.SCU, 0).toFixed(2)} SCU
          </span>
          {ownerLots.map((lot) => (
            <div key={lot.id} className="flex items-center justify-between text-sm">
              <span>{lot.Minerai}</span>
              <span className="font-mono">{lot.SCU} SCU</span>
              <span className="inline-flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${qualityDot(lot.Qualité)}`} />
                {lot.Qualité}/1000
              </span>
              {isAdmin && (
                <button
                  onClick={() => handleUnblock(lot.id)}
                  className="text-irr-dim hover:text-irr-text text-xs font-display font-semibold"
                >
                  Débloquer
                </button>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

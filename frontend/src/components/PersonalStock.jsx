import { useEffect, useState } from 'react'
import {
  getPersonalStock,
  relocatePersonalStock,
  consumePersonalStock,
  getAllTerminals,
} from '../lib/api'

const REASONS = ['Vendu', 'Détruit', 'Perdu', 'Donné', 'Autre']

function qualityDot(q) {
  if (q >= 700) return 'bg-irr-green'
  if (q >= 400) return 'bg-irr-amber'
  return 'bg-red-500'
}

export default function PersonalStock() {
  const [stock, setStock] = useState(null)
  const [terminals, setTerminals] = useState([])
  const [error, setError] = useState(null)
  const [openRow, setOpenRow] = useState(null)

  async function load() {
    try {
      setStock(await getPersonalStock())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    getAllTerminals().then(setTerminals).catch(() => {})
  }, [])

  async function handleRelocate(stockId, location) {
    await relocatePersonalStock(stockId, location)
    await load()
  }

  async function handleConsume(stockId, reason) {
    await consumePersonalStock(stockId, reason)
    await load()
  }

  if (error) return <div className="text-red-400 text-sm">{error}</div>
  if (stock === null) return <div className="text-irr-dim text-sm">Chargement…</div>
  if (stock.length === 0) return null

  return (
    <div className="flex flex-col gap-3">
      <span className="font-display font-bold text-sm tracking-wide uppercase text-irr-dim">
        Mon stock personnel
      </span>
      {stock.map((row) => (
        <div key={row.id} className="cut bg-irr-panel border border-irr-border p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-display font-semibold text-sm">{row.commodity_name}</span>
            <span className="font-mono text-sm">{row.quantity} SCU</span>
            <span className="inline-flex items-center gap-1.5 text-xs">
              <span className={`w-2 h-2 rounded-full ${qualityDot(row.quality)}`} />
              {row.quality}/1000
            </span>
          </div>
          <div className="text-xs text-irr-dim">📍 {row.location || '—'}</div>

          <div className="flex gap-2">
            <button
              onClick={() => setOpenRow(openRow === `move-${row.id}` ? null : `move-${row.id}`)}
              className="text-xs font-display font-semibold text-irr-dim hover:text-irr-text"
            >
              Transporter vers…
            </button>
            <button
              onClick={() => setOpenRow(openRow === `consume-${row.id}` ? null : `consume-${row.id}`)}
              className="text-xs font-display font-semibold text-irr-dim hover:text-irr-text"
            >
              Marquer comme consommé
            </button>
          </div>

          {openRow === `move-${row.id}` && (
            <RelocateForm
              terminals={terminals}
              onConfirm={(loc) => { handleRelocate(row.id, loc); setOpenRow(null) }}
            />
          )}
          {openRow === `consume-${row.id}` && (
            <ConsumeForm onConfirm={(reason) => { handleConsume(row.id, reason); setOpenRow(null) }} />
          )}
        </div>
      ))}
    </div>
  )
}

function RelocateForm({ terminals, onConfirm }) {
  const [dest, setDest] = useState('')
  return (
    <div className="flex gap-2 items-center">
      <select
        value={dest}
        onChange={(e) => setDest(e.target.value)}
        className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-xs text-irr-text flex-1 focus:outline-none focus:border-irr-accent"
      >
        <option value="">Choisir une station…</option>
        {terminals.map((t) => (
          <option key={t.id} value={t.name}>{t.name} ({t.star_system_name || '?'})</option>
        ))}
      </select>
      <button
        disabled={!dest}
        onClick={() => onConfirm(dest)}
        className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent text-xs font-display font-semibold px-3 py-1.5 disabled:opacity-50"
      >
        Confirmer
      </button>
    </div>
  )
}

function ConsumeForm({ onConfirm }) {
  const [reason, setReason] = useState(REASONS[0])
  return (
    <div className="flex gap-2 items-center">
      <select
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-xs text-irr-text flex-1 focus:outline-none focus:border-irr-accent"
      >
        {REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
      <button
        onClick={() => onConfirm(reason)}
        className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent text-xs font-display font-semibold px-3 py-1.5"
      >
        Confirmer
      </button>
    </div>
  )
}

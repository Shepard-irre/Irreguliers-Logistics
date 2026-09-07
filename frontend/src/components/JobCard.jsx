import { useState } from 'react'
import { VenteIcon, StockFederalIcon, PersonnelIcon } from './icons'

const DESTINATIONS = [
  { key: 'vente', label: 'Vente', Icon: VenteIcon, accent: 'amber' },
  { key: 'stock_federal', label: 'Stock Fédéral', Icon: StockFederalIcon, accent: 'accent' },
  { key: 'personnel', label: 'Personnel', Icon: PersonnelIcon, accent: 'violet' },
]

const ACCENT_CLASSES = {
  amber: 'bg-irr-amber-dim border-irr-amber text-irr-amber',
  accent: 'bg-irr-accent-dim border-irr-accent text-irr-accent',
  violet: 'bg-irr-violet-dim border-irr-violet text-irr-violet',
}

function cleanCommodityName(name) {
  return name.replace(/\s*\((Raw|Ore)\)\s*/gi, '').trim()
}

function qualityColor(quality) {
  if (quality >= 700) return 'bg-irr-green'
  if (quality >= 400) return 'bg-irr-amber'
  return 'bg-red-500'
}

export default function JobCard({ job, onConfirm, onCancel }) {
  const defaultQuality = job.quality || 500
  const defaultDestination = defaultQuality >= 750 ? 'stock_federal' : 'vente'
  const stationShortName = (job.terminal_name || '').split(' (')[0]

  const [quantityActual, setQuantityActual] = useState(job.quantity_estimated ?? 0)
  const [quality, setQuality] = useState(defaultQuality)
  const [destination, setDestination] = useState(defaultDestination)
  const [pickupLocation, setPickupLocation] = useState(stationShortName)
  const [personalLocation, setPersonalLocation] = useState(stationShortName)
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function handleConfirm() {
    setBusy(true)
    setError(null)
    try {
      await onConfirm(job.id, {
        quantity_actual: Number(quantityActual),
        quality: Number(quality),
        destination,
        pickup_location: destination === 'personnel' ? undefined : pickupLocation,
        personal_location: destination === 'personnel' ? personalLocation : undefined,
        notes: notes || undefined,
      })
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  async function handleCancel() {
    setBusy(true)
    setError(null)
    try {
      await onCancel(job.id)
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <div className="cut bg-irr-panel border border-irr-border p-6 flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <span className="font-display font-bold text-xl tracking-wide">
            {cleanCommodityName(job.commodity_name).toUpperCase()}
          </span>
          <span className="text-xs text-irr-dim">
            {job.terminal_name} — {job.method}
          </span>
        </div>
        <span className="cut-sm bg-irr-amber-dim border border-irr-amber text-irr-amber text-[10px] font-display font-semibold tracking-[0.14em] uppercase px-2.5 py-1">
          En attente
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 border-t border-b border-irr-border py-3.5">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Quantité obtenue (SCU)
          </span>
          <input
            type="number"
            min="0"
            step="0.5"
            value={quantityActual}
            onChange={(e) => setQuantityActual(e.target.value)}
            className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 font-mono text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Qualité (1-1000)
          </span>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${qualityColor(quality)} shrink-0`} />
            <input
              type="number"
              min="1"
              max="1000"
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 font-mono text-sm text-irr-text w-full focus:outline-none focus:border-irr-accent"
            />
          </div>
        </label>
      </div>

      <div className="flex items-center gap-3.5 flex-wrap">
        <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim shrink-0">
          Destination
        </span>
        <div className="flex gap-2.5">
          {DESTINATIONS.map(({ key, label, Icon, accent }) => {
            const selected = destination === key
            return (
              <button
                key={key}
                type="button"
                onClick={() => setDestination(key)}
                className={`cut-sm flex items-center gap-1.5 px-3.5 py-2 border font-display font-semibold text-[12.5px] tracking-wide ${
                  selected ? ACCENT_CLASSES[accent] : 'border-irr-border-strong text-irr-muted'
                }`}
              >
                <Icon />
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {destination === 'personnel' ? (
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Localisation des minerais
          </span>
          <input
            value={personalLocation}
            onChange={(e) => setPersonalLocation(e.target.value)}
            placeholder="ex: Aspis Station…"
            className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          />
        </label>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
              Lieu de pickup
            </span>
            <input
              value={pickupLocation}
              onChange={(e) => setPickupLocation(e.target.value)}
              className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
              Notes (optionnel)
            </span>
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
            />
          </label>
        </div>
      )}

      {error && <div className="text-red-400 text-xs">{error}</div>}

      <div className="flex gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={handleConfirm}
          className="cut-sm flex-1 bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide py-2 disabled:opacity-50"
        >
          Confirmer le raffinage
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={handleCancel}
          className="cut-sm px-5 border border-irr-border-strong text-irr-muted font-display font-semibold text-sm tracking-wide py-2 disabled:opacity-50"
        >
          Annuler
        </button>
      </div>
    </div>
  )
}

import { useState } from 'react'
import {
  getSessionDetail,
  closeSession,
  addSessionShip,
  removeSessionShip,
  addCrewMember,
  removeCrewMember,
  addSessionExpense,
  removeSessionExpense,
  getSessionFinancialSummary,
} from '../lib/api'

const STATUS_LABELS = {
  open: 'En cours',
  completed: 'Terminée',
  cancelled: 'Annulée',
}

const STATUS_CLASSES = {
  open: 'bg-irr-amber-dim border-irr-amber text-irr-amber',
  completed: 'bg-irr-green-dim border-irr-green text-irr-green',
  cancelled: 'border-irr-border-strong text-irr-dim',
}

function fmtAuec(n) {
  return `${Math.round(n).toLocaleString('fr-FR')} aUEC`
}

export default function SessionCard({ session, onChanged }) {
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  const [shipName, setShipName] = useState('')
  const [shipRole, setShipRole] = useState('mining')
  const [crewInputs, setCrewInputs] = useState({})
  const [expenseDesc, setExpenseDesc] = useState('')
  const [expenseAmount, setExpenseAmount] = useState(0)

  const isOpen = session.status === 'open'

  async function load() {
    setError(null)
    try {
      const [d, s] = await Promise.all([getSessionDetail(session.id), getSessionFinancialSummary(session.id)])
      setDetail(d)
      setSummary(s)
    } catch (e) {
      setError(e.message)
    }
  }

  async function toggle() {
    const next = !open
    setOpen(next)
    if (next && !detail) await load()
  }

  async function refreshAndReload() {
    await load()
    onChanged?.()
  }

  async function handleAddShip() {
    if (!shipName.trim()) return
    await addSessionShip(session.id, shipName.trim(), shipRole)
    setShipName('')
    await refreshAndReload()
  }

  async function handleAddCrew(shipId) {
    const name = (crewInputs[shipId] || '').trim()
    if (!name) return
    await addCrewMember(shipId, name)
    setCrewInputs((c) => ({ ...c, [shipId]: '' }))
    await refreshAndReload()
  }

  async function handleAddExpense() {
    if (!expenseDesc.trim() || expenseAmount <= 0) return
    await addSessionExpense(session.id, expenseDesc.trim(), Number(expenseAmount))
    setExpenseDesc('')
    setExpenseAmount(0)
    await refreshAndReload()
  }

  return (
    <div className="cut bg-irr-panel border border-irr-border flex flex-col">
      <button
        onClick={toggle}
        className="flex items-center justify-between px-6 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="font-display font-bold text-base tracking-wide">{session.numero}</span>
          <span className="text-irr-dim text-sm">— {session.star_system}</span>
        </div>
        <span className={`cut-sm border text-[10px] font-display font-semibold tracking-[0.14em] uppercase px-2.5 py-1 ${STATUS_CLASSES[session.status] || ''}`}>
          {STATUS_LABELS[session.status] || session.status}
        </span>
      </button>

      {open && (
        <div className="px-6 pb-6 flex flex-col gap-5 border-t border-irr-border pt-5">
          {error && <div className="text-red-400 text-xs">{error}</div>}
          {!detail ? (
            <div className="text-irr-dim text-sm">Chargement…</div>
          ) : (
            <>
              {isOpen && (
                <button
                  onClick={async () => { await closeSession(session.id); await refreshAndReload() }}
                  className="cut-sm self-start bg-irr-green-dim border border-irr-green text-irr-green font-display font-semibold text-xs tracking-wide px-4 py-2"
                >
                  Clore la session
                </button>
              )}

              <div className="flex flex-col gap-3">
                <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                  Vaisseaux
                </span>
                {detail.ships.length === 0 && <div className="text-irr-dim text-sm">Aucun vaisseau.</div>}
                {detail.ships.map((ship) => (
                  <div key={ship.id} className="bg-irr-panel-alt border border-irr-border p-3 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-display font-semibold">
                        {ship.ship_name} <span className="text-irr-dim font-normal">({ship.ship_role})</span>
                      </span>
                      {isOpen && (
                        <button
                          onClick={async () => { await removeSessionShip(ship.id); await refreshAndReload() }}
                          className="text-irr-dim hover:text-red-400 text-xs"
                        >
                          Retirer
                        </button>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {ship.crew.map((c) => (
                        <span key={c.id} className="flex items-center gap-1.5 bg-irr-panel border border-irr-border-strong px-2 py-1 text-xs">
                          {c.username}
                          {isOpen && (
                            <button
                              onClick={async () => { await removeCrewMember(c.id); await refreshAndReload() }}
                              className="text-irr-dim hover:text-red-400"
                            >
                              ×
                            </button>
                          )}
                        </span>
                      ))}
                    </div>
                    {isOpen && (
                      <div className="flex gap-2">
                        <input
                          value={crewInputs[ship.id] || ''}
                          onChange={(e) => setCrewInputs((c) => ({ ...c, [ship.id]: e.target.value }))}
                          placeholder="pseudo du joueur"
                          className="bg-irr-panel border border-irr-border-strong px-2 py-1 text-xs text-irr-text flex-1 focus:outline-none focus:border-irr-accent"
                        />
                        <button
                          onClick={() => handleAddCrew(ship.id)}
                          className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent text-xs font-display font-semibold px-3"
                        >
                          + Membre
                        </button>
                      </div>
                    )}
                  </div>
                ))}
                {isOpen && (
                  <div className="flex gap-2">
                    <input
                      value={shipName}
                      onChange={(e) => setShipName(e.target.value)}
                      placeholder="Nom du vaisseau"
                      className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text flex-1 focus:outline-none focus:border-irr-accent"
                    />
                    <select
                      value={shipRole}
                      onChange={(e) => setShipRole(e.target.value)}
                      className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
                    >
                      <option value="mining">Minage</option>
                      <option value="escort">Escorte</option>
                      <option value="transport">Transporteur</option>
                    </select>
                    <button
                      onClick={handleAddShip}
                      className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent text-sm font-display font-semibold px-4"
                    >
                      + Vaisseau
                    </button>
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-3">
                <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                  Frais de session
                </span>
                {detail.expenses.length === 0 && <div className="text-irr-dim text-sm">Aucun frais saisi.</div>}
                {detail.expenses.map((exp) => (
                  <div key={exp.id} className="flex items-center justify-between text-sm">
                    <span>{exp.description}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-mono">{fmtAuec(exp.amount_auec)}</span>
                      {isOpen && (
                        <button
                          onClick={async () => { await removeSessionExpense(exp.id); await refreshAndReload() }}
                          className="text-irr-dim hover:text-red-400 text-xs"
                        >
                          Retirer
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {isOpen && (
                  <div className="flex gap-2">
                    <input
                      value={expenseDesc}
                      onChange={(e) => setExpenseDesc(e.target.value)}
                      placeholder="Carburant Prospector"
                      className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 text-sm text-irr-text flex-1 focus:outline-none focus:border-irr-accent"
                    />
                    <input
                      type="number"
                      min="0"
                      value={expenseAmount}
                      onChange={(e) => setExpenseAmount(e.target.value)}
                      className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1.5 font-mono text-sm text-irr-text w-32 focus:outline-none focus:border-irr-accent"
                    />
                    <button
                      onClick={handleAddExpense}
                      className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent text-sm font-display font-semibold px-4"
                    >
                      +
                    </button>
                  </div>
                )}
              </div>

              {summary && (
                <div className="flex flex-col gap-3 border-t border-irr-border pt-4">
                  <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                    Rapport financier
                  </span>
                  {!summary.has_orders ? (
                    <div className="text-irr-dim text-sm">Aucun bon de transport rattaché à cette session.</div>
                  ) : (
                    <>
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <FinTile label="Recette estimée" value={fmtAuec(summary.total_vente_auec)} />
                        <FinTile label="Part Fédération (20%)" value={fmtAuec(summary.part_federation)} />
                        <FinTile label="Part Transport (15%)" value={fmtAuec(summary.part_transport)} />
                        <FinTile label="Frais vaisseaux" value={fmtAuec(summary.total_expenses)} />
                        <FinTile label="Reste à partager" value={fmtAuec(summary.reste_a_partager)} />
                        <FinTile
                          label={`Salaire/joueur (${summary.nb_joueurs})`}
                          value={fmtAuec(summary.salaire_par_joueur)}
                          accent
                        />
                      </div>
                      {summary.crew.length > 0 && (
                        <div className="text-xs text-irr-dim">Mineurs présents : {summary.crew.join(', ')}</div>
                      )}
                      <SettlementBlock
                        title="Règlement stock personnel"
                        settlement={summary.personnel_settlement}
                      />
                      <SettlementBlock
                        title="Règlement stock fédération"
                        settlement={summary.federal_settlement}
                      />
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

function SettlementBlock({ title, settlement }) {
  if (!settlement) return null
  return (
    <div className="flex flex-col gap-3 border-t border-irr-border pt-4">
      <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
        {title}
      </span>
      <div className="text-xs text-irr-text">
        <span className="text-irr-accent font-semibold">{settlement.payer}</span> doit{' '}
        <span className="font-mono font-semibold">{fmtAuec(settlement.salaire_par_joueur)}</span> à chaque membre ayant participé.
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <FinTile label="Recette estimée" value={fmtAuec(settlement.recette)} />
        <FinTile label="Part Fédération (20%)" value={fmtAuec(settlement.part_federation)} />
        <FinTile label="Part Transport (15%)" value={fmtAuec(settlement.part_transport)} />
        <FinTile label="Reste à partager" value={fmtAuec(settlement.reste)} />
        <FinTile label="Salaire/joueur" value={fmtAuec(settlement.salaire_par_joueur)} accent />
      </div>
    </div>
  )
}

function FinTile({ label, value, accent }) {
  return (
    <div className="bg-irr-panel-alt border border-irr-border p-3 flex flex-col gap-1">
      <span className="text-[9.5px] font-display font-semibold tracking-[0.1em] uppercase text-irr-dim">{label}</span>
      <span className={`font-mono font-semibold ${accent ? 'text-irr-accent' : 'text-irr-text'}`}>{value}</span>
    </div>
  )
}

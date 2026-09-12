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
  renameSession,
} from '../lib/api'
import { useAuth } from '../context/AuthContext'

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

export default function SessionCard({ session, onChanged, members = [] }) {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [renaming, setRenaming] = useState(false)
  const [newNumero, setNewNumero] = useState(session.numero)

  const isResponsible = user && user.username === session.created_by

  async function handleRename() {
    if (!newNumero.trim() || newNumero === session.numero) {
      setRenaming(false)
      return
    }
    await renameSession(session.id, newNumero.trim())
    setRenaming(false)
    onChanged?.()
  }

  const [shipName, setShipName] = useState('')
  const [shipRole, setShipRole] = useState('mining')
  const [crewInputs, setCrewInputs] = useState({})
  const [expenseDesc, setExpenseDesc] = useState('')
  const [expenseAmount, setExpenseAmount] = useState(0)

  const isOpen = session.status === 'open'

  async function load() {
    setError(null)
    try {
      setDetail(await getSessionDetail(session.id))
    } catch (e) {
      setError(e.message)
      return
    }
    try {
      setSummary(await getSessionFinancialSummary(session.id))
    } catch {
      // 403 for users outside the financial-report allowlist — the rest of the
      // session (ships, crew, expenses) still loaded fine, just hide that section.
      setSummary(null)
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
      <div
        onClick={renaming ? undefined : toggle}
        className="flex items-center justify-between px-6 py-4 text-left cursor-pointer"
      >
        <div className="flex items-center gap-3">
          {renaming ? (
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <input
                value={newNumero}
                onChange={(e) => setNewNumero(e.target.value)}
                autoFocus
                className="bg-irr-panel-alt border border-irr-border-strong px-2 py-1 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
              />
              <button
                onClick={handleRename}
                className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent text-xs font-display font-semibold px-2 py-1"
              >
                OK
              </button>
              <button
                onClick={() => { setNewNumero(session.numero); setRenaming(false) }}
                className="text-irr-dim hover:text-irr-text text-xs"
              >
                Annuler
              </button>
            </div>
          ) : (
            <>
              <span className="font-display font-bold text-base tracking-wide">{session.numero}</span>
              {isResponsible && (
                <button
                  onClick={(e) => { e.stopPropagation(); setNewNumero(session.numero); setRenaming(true) }}
                  className="text-irr-dim hover:text-irr-accent text-xs"
                  title="Renommer la session"
                >
                  ✎
                </button>
              )}
            </>
          )}
          <span className="text-irr-dim text-sm">— {session.star_system}</span>
        </div>
        <span className={`cut-sm border text-[10px] font-display font-semibold tracking-[0.14em] uppercase px-2.5 py-1 ${STATUS_CLASSES[session.status] || ''}`}>
          {STATUS_LABELS[session.status] || session.status}
        </span>
      </div>

      {open && (
        <div className="px-6 pb-6 flex flex-col gap-5 border-t border-irr-border pt-5">
          <datalist id={`irr-members-${session.id}`}>
            {members.map((m) => (
              <option key={m.username} value={m.username} />
            ))}
          </datalist>
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
                          list={`irr-members-${session.id}`}
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
                      {summary.crew.length > 0 && (
                        <div className="text-xs text-irr-dim">Mineurs présents : {summary.crew.join(', ')}</div>
                      )}
                      <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
                        Récapitulatif global
                      </span>
                      <div className="grid grid-cols-3 gap-3 text-sm">
                        <FinTile label="Recette globale estimée" value={fmtAuec(summary.recap_global.recette_globale)} />
                        <FinTile label="Participation Fédération" value={fmtAuec(summary.recap_global.participation_federation)} />
                        <FinTile label="Part Transporteurs" value={fmtAuec(summary.recap_global.part_transporteurs)} />
                        <FinTile label="Coût d'entretien" value={fmtAuec(summary.recap_global.cout_entretien)} />
                        <FinTile label="Coût total membres (hors transport)" value={fmtAuec(summary.recap_global.cout_total_membres)} />
                        <FinTile label="Salaire global d'un membre" value={fmtAuec(summary.recap_global.salaire_global_membre)} accent />
                      </div>
                      <SettlementBlock title="Règlement stock personnel" settlement={summary.personnel_settlement} kind="personnel" />
                      <SettlementBlock title="Règlement vente" settlement={summary.vente_settlement} kind="vente" />
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

function SettlementBlock({ title, settlement, kind }) {
  if (!settlement) return null
  const owesTransport = kind !== 'vente' && settlement.part_transport > 0
  const keepsTransport = kind === 'vente' && settlement.part_transport > 0

  return (
    <div className="flex flex-col gap-3 border-t border-irr-border pt-4">
      <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
        {title}
      </span>
      <div className="text-xs text-irr-text">
        <span className="text-irr-accent font-semibold">{settlement.payer}</span> — recette estimée{' '}
        <span className="font-mono font-semibold">{fmtAuec(settlement.recette)}</span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <FinTile label={`${settlement.payer} doit à la Fédération`} value={fmtAuec(settlement.part_federation)} />
        {owesTransport && (
          <FinTile label={`${settlement.payer} doit aux Transporteurs`} value={fmtAuec(settlement.part_transport)} />
        )}
        {keepsTransport && (
          <FinTile label="Leur part (gardée)" value={fmtAuec(settlement.part_transport)} />
        )}
        {settlement.expenses > 0 && <FinTile label="Frais vaisseaux" value={fmtAuec(settlement.expenses)} />}
        <FinTile
          label={`${settlement.payer} doit à chaque autre participant`}
          value={fmtAuec(settlement.salaire_par_joueur)}
          accent
        />
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

import { useEffect, useState } from 'react'
import SessionCard from './SessionCard'
import { getSessions, createSession, getMembers } from '../lib/api'

const STAR_SYSTEMS = ['Stanton', 'Pyro', 'Nyx']

export default function SessionsTab() {
  const [sessions, setSessions] = useState(null)
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [newSystem, setNewSystem] = useState(STAR_SYSTEMS[0])

  async function load() {
    try {
      setSessions(await getSessions())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    getMembers().then(setMembers).catch(() => setMembers([]))
  }, [])

  async function handleCreate() {
    await createSession(newSystem)
    await load()
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="cut bg-irr-panel border border-irr-border p-5 flex items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Créer une session — système
          </span>
          <select
            value={newSystem}
            onChange={(e) => setNewSystem(e.target.value)}
            className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          >
            {STAR_SYSTEMS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <button
          onClick={handleCreate}
          className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide px-5 py-2"
        >
          Créer la session
        </button>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}
      {sessions === null && !error && <div className="text-irr-dim text-sm">Chargement…</div>}
      {sessions && sessions.length === 0 && <div className="text-irr-dim text-sm">Aucune session de minage.</div>}

      <div className="flex flex-col gap-3">
        {(sessions || []).map((s) => (
          <SessionCard key={s.id} session={s} onChanged={load} members={members} />
        ))}
      </div>
    </div>
  )
}

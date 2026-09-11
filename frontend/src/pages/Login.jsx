import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, ssoError } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username, password)
    } catch (err) {
      setError(err.message || 'Identifiants invalides')
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form
        onSubmit={handleSubmit}
        className="cut bg-irr-panel border border-irr-border p-8 w-[360px] flex flex-col gap-5"
      >
        <div className="flex flex-col items-center gap-2 mb-2">
          <img src="/logo.png" alt="Les Irréguliers" width="40" height="40" />
          <div className="font-display font-bold text-lg tracking-wide">LES IRRÉGULIERS</div>
          <div className="text-irr-accent text-[10px] font-display font-semibold tracking-[0.14em] uppercase">
            Console Fédérale
          </div>
        </div>

        {ssoError && (
          <div className="text-red-400 text-xs">Échec de la connexion automatique : {ssoError}</div>
        )}

        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Identifiant
          </span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
            Mot de passe
          </span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="bg-irr-panel-alt border border-irr-border-strong px-3 py-2 text-sm text-irr-text focus:outline-none focus:border-irr-accent"
          />
        </label>

        {error && <div className="text-red-400 text-xs">{error}</div>}

        <button
          type="submit"
          disabled={busy}
          className="cut-sm bg-irr-accent-dim border border-irr-accent text-irr-accent font-display font-semibold text-sm tracking-wide py-2.5 disabled:opacity-50"
        >
          Connexion
        </button>
      </form>
    </div>
  )
}

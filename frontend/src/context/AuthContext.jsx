import { createContext, useContext, useEffect, useState } from 'react'
import { login as apiLogin, sso as apiSso, getStoredUser, storeSession, clearSession } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser())

  useEffect(() => {
    if (user) return
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (!token) return
    apiSso(token).then((data) => {
      storeSession(data.access_token, data.user)
      setUser(data.user)
      params.delete('token')
      const rest = params.toString()
      window.history.replaceState({}, '', window.location.pathname + (rest ? `?${rest}` : ''))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function login(username, password) {
    const data = await apiLogin(username, password)
    storeSession(data.access_token, data.user)
    setUser(data.user)
  }

  function logout() {
    clearSession()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

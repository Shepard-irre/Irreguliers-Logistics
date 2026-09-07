import { createContext, useContext, useState } from 'react'
import { login as apiLogin, getStoredUser, storeSession, clearSession } from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser())

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

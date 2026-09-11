import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('../lib/api', () => ({
  login: vi.fn(),
  sso: vi.fn(),
  getStoredUser: vi.fn(() => null),
  storeSession: vi.fn(),
  clearSession: vi.fn(),
}))

import { sso } from '../lib/api'
import { AuthProvider, useAuth } from './AuthContext'

function Probe() {
  const { user } = useAuth()
  return <div>{user ? user.username : 'anonyme'}</div>
}

beforeEach(() => {
  window.history.pushState({}, '', '/')
})

describe('AuthContext — SSO via token en URL', () => {
  it("se connecte automatiquement quand l'URL contient ?token=... au montage", async () => {
    window.history.pushState({}, '', '/?token=abc123')
    sso.mockResolvedValue({ access_token: 'jwt-xyz', user: { username: 'Shepard40' } })

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(await screen.findByText('Shepard40')).toBeInTheDocument()
    expect(sso).toHaveBeenCalledWith('abc123')
  })

  it('retire le token de l\'URL une fois connecté', async () => {
    window.history.pushState({}, '', '/?token=abc123')
    sso.mockResolvedValue({ access_token: 'jwt-xyz', user: { username: 'Shepard40' } })

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    await screen.findByText('Shepard40')
    expect(window.location.search).toBe('')
  })

  it('ne fait rien sans token dans l\'URL', async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    )

    expect(await screen.findByText('anonyme')).toBeInTheDocument()
    expect(sso).not.toHaveBeenCalled()
  })
})

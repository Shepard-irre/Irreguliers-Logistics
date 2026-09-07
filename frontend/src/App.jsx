import { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Raffineries from './pages/Raffineries'
import Commerce from './pages/Commerce'
import GestionStock from './pages/GestionStock'
import StockFederation from './pages/StockFederation'
import CommerceFederation from './pages/CommerceFederation'
import Transport from './pages/Transport'
import Crafting from './pages/Crafting'
import Admin from './pages/Admin'

const PAGES = {
  raffineries: Raffineries,
  commerce: Commerce,
  'gestion-stock': GestionStock,
  'stock-federation': StockFederation,
  'commerce-federation': CommerceFederation,
  transport: Transport,
  crafting: Crafting,
  admin: Admin,
}

function AppContent() {
  const { user } = useAuth()
  const [page, setPage] = useState('raffineries')

  if (!user) return <Login />

  const PageComponent = PAGES[page] || Raffineries

  return (
    <div className="flex min-h-screen">
      <Sidebar active={page} onNavigate={setPage} />
      <div className="flex-1 flex flex-col min-w-0">
        <PageComponent />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

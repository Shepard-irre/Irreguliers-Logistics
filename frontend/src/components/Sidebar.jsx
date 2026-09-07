import {
  RaffineriesIcon,
  CommerceIcon,
  InventaireIcon,
  StockFederalIcon,
  TransportIcon,
  CraftingIcon,
  AdminIcon,
} from './icons'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { key: 'raffineries', label: 'Raffineries', Icon: RaffineriesIcon, permission: 'page_raffineries' },
  { key: 'commerce', label: 'Commerce', Icon: CommerceIcon, permission: 'page_commerce' },
  { key: 'gestion-stock', label: 'Gestion de stock', Icon: InventaireIcon, permission: 'page_gestion_stock' },
  { key: 'stock-federation', label: 'Stock Fédération', Icon: StockFederalIcon, permission: 'page_stock_federation' },
  { key: 'commerce-federation', label: 'Commerce Fédération', Icon: StockFederalIcon, permission: 'page_commerce_federation' },
  { key: 'transport', label: 'Transport', Icon: TransportIcon, permission: 'page_transport' },
  { key: 'crafting', label: 'Crafting', Icon: CraftingIcon, permission: 'page_crafting' },
  { key: 'admin', label: 'Admin', Icon: AdminIcon, permission: 'admin_panel' },
]

const IMPLEMENTED = new Set(['raffineries', 'commerce', 'gestion-stock', 'stock-federation', 'commerce-federation', 'transport', 'crafting', 'admin'])

export default function Sidebar({ active, onNavigate }) {
  const { user, logout } = useAuth()
  const permissions = user?.permissions || []
  const isAdmin = permissions.includes('admin_panel')

  const visibleItems = NAV_ITEMS.filter(
    (item) => permissions.includes(item.permission) || (item.key === 'transport' && isAdmin),
  )

  return (
    <div className="w-64 shrink-0 bg-irr-panel border-r border-irr-border flex flex-col p-6">
      <div className="flex items-center gap-3">
        <img src="/logo.png" alt="Les Irréguliers" width="34" height="34" className="shrink-0" />
        <div className="flex flex-col leading-tight">
          <div className="font-display font-bold text-base tracking-wide">LES IRRÉGULIERS</div>
          <div className="text-irr-accent text-[10px] font-display font-semibold tracking-[0.14em] uppercase">
            Console Fédérale
          </div>
        </div>
      </div>

      <nav className="flex flex-col gap-1 mt-9">
        {visibleItems.map(({ key, label, Icon }) => {
          const isActive = key === active
          const implemented = IMPLEMENTED.has(key)
          return (
            <button
              key={key}
              onClick={() => implemented && onNavigate(key)}
              disabled={!implemented}
              title={implemented ? undefined : 'Pas encore porté depuis Streamlit'}
              className={`flex items-center gap-3 px-3 py-2.5 font-display font-semibold text-sm tracking-wide text-left ${
                isActive
                  ? 'bg-irr-accent-dim border-l-2 border-irr-accent text-irr-text'
                  : implemented
                    ? 'text-irr-muted hover:text-irr-text cursor-pointer'
                    : 'text-irr-dim cursor-not-allowed'
              }`}
            >
              <Icon className={isActive ? 'text-irr-accent' : undefined} />
              <span>{label}</span>
            </button>
          )
        })}
      </nav>

      <div className="grow" />

      <div className="border-t border-irr-border pt-4 flex items-center gap-3">
        <div className="w-9 h-9 bg-irr-panel-alt border border-irr-border-strong cut-sm flex items-center justify-center shrink-0">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="text-irr-muted">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21c0-4 4-6 8-6s8 2 8 6" strokeLinecap="round" />
          </svg>
        </div>
        <div className="flex flex-col leading-tight min-w-0">
          <div className="font-display font-semibold text-sm truncate">{user?.username}</div>
          <div className="text-[10.5px] text-irr-dim tracking-wide truncate">
            {user?.roles?.[0]?.name || '—'}
          </div>
        </div>
        <button
          onClick={logout}
          className="ml-auto text-irr-dim hover:text-irr-text text-xs font-display font-semibold shrink-0"
        >
          Sortir
        </button>
      </div>
    </div>
  )
}

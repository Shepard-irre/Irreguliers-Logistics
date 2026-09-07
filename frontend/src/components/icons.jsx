const base = { fill: 'none', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }

export function RaffineriesIcon({ size = 19, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <path d="M4 21V10l5-6 5 6v11" />
      <path d="M14 21V13l4-4 2 2v10" />
      <path d="M4 21h16" />
    </svg>
  )
}

export function CommerceIcon({ size = 19, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <path d="M3 8h13M16 8l-3-3M16 8l-3 3" />
      <path d="M21 16H8M8 16l3-3M8 16l3 3" />
    </svg>
  )
}

export function InventaireIcon({ size = 19, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <path d="M21 8l-9-5-9 5 9 5 9-5z" />
      <path d="M3 8v8l9 5 9-5V8" />
      <path d="M12 13v8" />
    </svg>
  )
}

export function AdminIcon({ size = 19, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
    </svg>
  )
}

export function VenteIcon({ size = 14, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} fill="none" strokeWidth={1.8} stroke="currentColor">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 8v8M9 10h4.5a1.75 1.75 0 0 1 0 3.5H9M9 13.5h5" strokeLinecap="round" />
    </svg>
  )
}

export function StockFederalIcon({ size = 14, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} fill="none" strokeWidth={1.8} stroke="currentColor">
      <ellipse cx="12" cy="6" rx="7" ry="3" />
      <path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6" strokeLinecap="round" />
      <path d="M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" strokeLinecap="round" />
    </svg>
  )
}

export function TransportIcon({ size = 19, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <path d="M3 16V7a1 1 0 0 1 1-1h9v10" />
      <path d="M13 10h4l4 4v2h-2" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="17" cy="18" r="2" />
    </svg>
  )
}

export function CraftingIcon({ size = 19, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <path d="M14.5 6.5a3 3 0 0 0-4.2 3.9L4 17v3h3l6.6-6.6a3 3 0 0 0 3.9-4.2l-2.2 2.2-2-2z" />
    </svg>
  )
}

export function PersonnelIcon({ size = 14, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className={className} {...base} stroke="currentColor">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" />
    </svg>
  )
}

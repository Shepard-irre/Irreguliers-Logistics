export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 border-b border-irr-border">
      {tabs.map((tab) => {
        const isActive = tab.key === active
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={`px-4 py-2.5 font-display font-semibold text-sm tracking-wide border-b-2 -mb-px ${
              isActive
                ? 'border-irr-accent text-irr-accent'
                : 'border-transparent text-irr-muted hover:text-irr-text'
            }`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}

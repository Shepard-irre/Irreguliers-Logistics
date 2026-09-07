export default function Topbar({ title, subtitle }) {
  return (
    <div className="h-[66px] border-b border-irr-border flex items-center justify-between px-8 shrink-0">
      <div className="flex items-baseline gap-3">
        <span className="font-display font-bold text-lg tracking-wide">{title}</span>
        {subtitle && <span className="text-irr-dim text-sm">/ {subtitle}</span>}
      </div>
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2 text-[11.5px] text-irr-muted tracking-wide">
          <div className="w-1.5 h-1.5 rounded-full bg-irr-accent pulse" />
          API UEX · EN LIGNE
        </div>
      </div>
    </div>
  )
}

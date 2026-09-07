import Topbar from '../components/Topbar'

export default function Admin() {
  return (
    <>
      <Topbar title="ADMIN" subtitle="Gestion utilisateurs" />
      <div className="flex-1 p-8">
        <div className="cut bg-irr-panel border border-irr-border p-5 text-sm text-irr-muted">
          La gestion des utilisateurs et des rôles se fait directement sur WordPress.
        </div>
      </div>
    </>
  )
}

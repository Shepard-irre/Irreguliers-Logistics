import { useEffect, useState } from 'react'
import Topbar from '../components/Topbar'
import Tabs from '../components/Tabs'
import JobCard from '../components/JobCard'
import NewJobForm from '../components/NewJobForm'
import SessionsTab from '../components/SessionsTab'
import PersonalStock from '../components/PersonalStock'
import CommodityLots from '../components/CommodityLots'
import { getRaffineriesJobs, confirmRaffineriesJob, cancelRaffineriesJob } from '../lib/api'

const TABS = [
  { key: 'sessions', label: 'Sessions de minage' },
  { key: 'estimation', label: 'Nouvelle estimation' },
  { key: 'jobs', label: 'Jobs en attente' },
  { key: 'stock', label: 'Stock personnel' },
]

export default function Raffineries() {
  const [activeTab, setActiveTab] = useState('jobs')
  const [jobs, setJobs] = useState(null)
  const [error, setError] = useState(null)

  async function loadJobs() {
    try {
      setJobs(await getRaffineriesJobs())
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [])

  async function handleConfirm(jobId, payload) {
    await confirmRaffineriesJob(jobId, payload)
    await loadJobs()
  }

  async function handleCancel(jobId) {
    await cancelRaffineriesJob(jobId)
    await loadJobs()
  }

  const totalScu = (jobs || []).reduce((sum, j) => sum + (j.quantity_estimated || 0), 0)
  const avgQuality = jobs?.length
    ? Math.round(jobs.reduce((sum, j) => sum + (j.quality || 0), 0) / jobs.length)
    : 0

  return (
    <>
      <Topbar title="RAFFINERIES" subtitle={TABS.find((t) => t.key === activeTab)?.label} />

      <div className="px-8 pt-5">
        <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />
      </div>

      <div className="flex-1 p-8 flex flex-col gap-6">
        {activeTab === 'sessions' && <SessionsTab />}

        {activeTab === 'estimation' && (
          <NewJobForm onCreated={() => { loadJobs(); setActiveTab('jobs') }} onClose={() => setActiveTab('jobs')} />
        )}

        {activeTab === 'jobs' && (
          <>
            <div className="grid grid-cols-3 gap-4">
              <StatTile label="Jobs actifs" value={jobs?.length ?? '—'} />
              <StatTile label="SCU en attente" value={jobs ? totalScu.toLocaleString('fr-FR') : '—'} />
              <StatTile label="Qualité moyenne" value={jobs?.length ? `${avgQuality}%` : '—'} accent />
            </div>

            {error && (
              <div className="cut bg-irr-panel border border-irr-border p-4 text-red-400 text-sm">
                {error}
              </div>
            )}

            {jobs === null && !error && (
              <div className="text-irr-dim text-sm">Chargement…</div>
            )}

            {jobs && jobs.length === 0 && (
              <div className="text-irr-dim text-sm">Aucun job de raffinage en attente.</div>
            )}

            <div className="flex flex-col gap-4">
              {(jobs || []).map((job) => (
                <JobCard key={job.id} job={job} onConfirm={handleConfirm} onCancel={handleCancel} />
              ))}
            </div>
          </>
        )}

        {activeTab === 'stock' && <PersonalStock />}

        <CommodityLots />
      </div>
    </>
  )
}

function StatTile({ label, value, accent }) {
  return (
    <div className="cut bg-irr-panel border border-irr-border p-4 flex flex-col gap-1.5">
      <span className="text-[11px] font-display font-semibold tracking-[0.14em] uppercase text-irr-dim">
        {label}
      </span>
      <span className={`font-mono font-semibold text-2xl ${accent ? 'text-irr-accent' : 'text-irr-text'}`}>
        {value}
      </span>
    </div>
  )
}

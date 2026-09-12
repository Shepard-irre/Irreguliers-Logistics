import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../lib/api', () => ({
  getRaffineriesReferenceData: vi.fn(),
  estimateRaffineriesJob: vi.fn(),
  createRaffineriesJob: vi.fn(),
  analyzeScreenshot: vi.fn(),
}))

import { getRaffineriesReferenceData, analyzeScreenshot, estimateRaffineriesJob, createRaffineriesJob } from '../lib/api'
import NewJobForm from './NewJobForm'

const REF_DATA = {
  commodities: [{ id: 1, name: 'Quantainium (Raw)' }, { id: 2, name: 'Agricium (Raw)' }],
  terminals: [{ id: 10, name: 'HDMS-Hadley', star_system_name: 'Stanton' }],
  methods: [{ name: 'Cormack' }],
  sessions: [{ id: 1, numero: 'MIN001', star_system: 'Stanton' }],
}

async function selectSession(user, label = 'MIN001 — Stanton') {
  await waitFor(() => expect(screen.getByLabelText('Session de minage')).toBeInTheDocument())
  await user.selectOptions(screen.getByLabelText('Session de minage'), label)
}

const REF_DATA_MULTI_SYSTEM = {
  commodities: [{ id: 1, name: 'Quantainium (Raw)' }],
  terminals: [
    { id: 10, name: 'HDMS-Hadley', star_system_name: 'Stanton' },
    { id: 20, name: 'Ashland Sallow', star_system_name: 'Pyro' },
  ],
  methods: [{ name: 'Cormack' }],
  sessions: [
    { id: 1, numero: 'MIN001', star_system: 'Stanton' },
    { id: 2, numero: 'MIN002', star_system: 'Pyro' },
  ],
}

describe('NewJobForm — mode batch', () => {
  it('ajoute un lot à la liste "Lots à raffiner" quand on clique sur + Ajouter', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA)
    const user = userEvent.setup()

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)

    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())
    await selectSession(user)
    await user.click(screen.getByText('+ Ajouter'))

    expect(await screen.findByText('Lots à raffiner')).toBeInTheDocument()
    // "Quantainium (Raw)" appears twice: once as the select option, once as
    // the label of the line we just added to the batch list.
    expect(screen.getAllByText('Quantainium (Raw)')).toHaveLength(2)
  })

  it('retire un lot de la liste au clic sur Retirer', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA)
    const user = userEvent.setup()

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)

    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())
    await selectSession(user)
    await user.click(screen.getByText('+ Ajouter'))
    await screen.findByText('Lots à raffiner')

    await user.click(screen.getByText('Retirer'))

    expect(screen.queryByText('Lots à raffiner')).not.toBeInTheDocument()
  })

  it('refuse d\'ajouter un lot de moins de 100 cSCU (1 SCU, unité minimale)', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA)
    const user = userEvent.setup()

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)

    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())
    await selectSession(user)
    const qtyInput = screen.getByLabelText('Quantité (cSCU)')
    await user.clear(qtyInput)
    await user.type(qtyInput, '40')
    await user.click(screen.getByText('+ Ajouter'))

    expect(screen.queryByText('Lots à raffiner')).not.toBeInTheDocument()
    expect(await screen.findByText(/Quantité minimum/)).toBeInTheDocument()
  })

  it('refuse d\'ajouter un lot ou d\'analyser un screenshot sans session sélectionnée', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA)

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())

    expect(screen.getByText('+ Ajouter')).toBeDisabled()
    expect(screen.getByText('Analyser le screenshot')).toBeDisabled()
    expect(screen.getByText(/Sélectionne une session de minage/)).toBeInTheDocument()
  })

  it('importe automatiquement les lots actifs d\'un screenshot TYPE B analysé', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA)
    analyzeScreenshot.mockResolvedValue({
      screen_type: 'B',
      terminal_name: null,
      method: null,
      lines: [
        { name: 'Quantainium', quality: 700, quantity_raw: 2000, quantity_refined: 1600, active: true },
        { name: 'Agricium', quality: 500, quantity_raw: 500, quantity_refined: null, active: false },
      ],
    })
    const user = userEvent.setup()

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())
    await selectSession(user)

    const file = new File(['fake-bytes'], 'shot.png', { type: 'image/png' })
    const fileInput = screen.getByLabelText('Screenshot raffinerie')
    await user.upload(fileInput, file)
    await user.click(screen.getByText('Analyser le screenshot'))

    expect(analyzeScreenshot).toHaveBeenCalledWith(file)
    // Only the active line (Quantainium) is imported; the inactive one (Agricium) is skipped.
    expect(await screen.findByText('Lots à raffiner')).toBeInTheDocument()
    expect(screen.getAllByText('Quantainium (Raw)')).toHaveLength(2)
    expect(screen.queryAllByText('Agricium (Raw)')).toHaveLength(1) // only the <option>, no line
  })

  it('reste utilisable quand on change de session de minage après avoir choisi une station de raffinage', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA_MULTI_SYSTEM)
    estimateRaffineriesJob.mockResolvedValue({
      estimated_output: 80, yield_pct: 80, confidence: 'Élevée', audit_count: 5,
    })
    createRaffineriesJob.mockResolvedValue({ id: 1 })
    const user = userEvent.setup()

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)
    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())

    // Terminal auto-selects HDMS-Hadley (Stanton) once the Stanton session is picked.
    await selectSession(user, 'MIN001 — Stanton')
    await user.click(screen.getByText('+ Ajouter'))
    await screen.findByText('Lots à raffiner')

    // Switching to a Pyro session re-filters the terminal list — HDMS-Hadley (Stanton) drops out.
    await user.selectOptions(screen.getByLabelText('Session de minage'), 'MIN002 — Pyro')

    await user.click(screen.getByText('Calculer l\'estimation pour tous les lots'))
    await screen.findByText('Enregistrer tous les lots restants')
    await user.click(screen.getByText('Enregistrer tous les lots restants'))

    await waitFor(() => expect(createRaffineriesJob).toHaveBeenCalled())
    expect(createRaffineriesJob.mock.calls[0][0].terminal_name).toContain('Ashland Sallow')
    expect(screen.queryByText(/Cannot read properties of undefined/)).not.toBeInTheDocument()
  })
})

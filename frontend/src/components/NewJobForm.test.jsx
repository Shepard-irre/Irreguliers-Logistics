import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../lib/api', () => ({
  getRaffineriesReferenceData: vi.fn(),
  estimateRaffineriesJob: vi.fn(),
  createRaffineriesJob: vi.fn(),
  analyzeScreenshot: vi.fn(),
}))

import { getRaffineriesReferenceData, analyzeScreenshot } from '../lib/api'
import NewJobForm from './NewJobForm'

const REF_DATA = {
  commodities: [{ id: 1, name: 'Quantainium (Raw)' }, { id: 2, name: 'Agricium (Raw)' }],
  terminals: [{ id: 10, name: 'HDMS-Hadley', star_system_name: 'Stanton' }],
  methods: [{ name: 'Cormack' }],
  sessions: [],
}

describe('NewJobForm — mode batch', () => {
  it('ajoute un lot à la liste "Lots à raffiner" quand on clique sur + Ajouter', async () => {
    getRaffineriesReferenceData.mockResolvedValue(REF_DATA)
    const user = userEvent.setup()

    render(<NewJobForm onCreated={() => {}} onClose={() => {}} />)

    await waitFor(() => expect(screen.getByText('+ Ajouter')).toBeInTheDocument())
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
    const qtyInput = screen.getByLabelText('Quantité (cSCU)')
    await user.clear(qtyInput)
    await user.type(qtyInput, '40')
    await user.click(screen.getByText('+ Ajouter'))

    expect(screen.queryByText('Lots à raffiner')).not.toBeInTheDocument()
    expect(await screen.findByText(/Quantité minimum/)).toBeInTheDocument()
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
})

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Occurrence } from '../../shared/api/types'
import { renderWithProviders, stubFetch } from '../../test/render'
import { OccurrenceRow } from './CyclePage'

const occ: Occurrence = {
  id: 'occ-1', version: 3, week_start: '2026-10-12', planned_on: '2026-10-12', window: 'before', status: 'pending',
  skip_reason: null, actual_minutes: 0, completed_on: null, suggested_topic_id: 'B01.01',
  slot: { code: 'S01', title: 'Estado e sociedade', purpose: 'basic', activity: 'theory', minutes: 60,
    selection_mode: 'alternate_subjects', candidate_topic_ids: ['B01.01'] },
}

afterEach(() => vi.unstubAllGlobals())

describe('OccurrenceRow', () => {
  it('não dispensa o bloco quando o usuário cancela o motivo', async () => {
    const fetchMock = stubFetch([])
    vi.stubGlobal('prompt', vi.fn(() => null))
    renderWithProviders(<ul><OccurrenceRow occ={occ} /></ul>)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Dispensar' }))
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

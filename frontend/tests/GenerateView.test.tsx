// Component test for GenerateView's loading/result/no-events states.
// Written before the real component exists (T017-T019) -- expected to fail
// until then. GenerateView is currently a placeholder.
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../src/api/client'
import type { CalendarResponse } from '../src/api/client'
import GenerateView from '../src/pages/GenerateView'

vi.mock('../src/api/client', async () => {
  const actual = await vi.importActual<typeof import('../src/api/client')>('../src/api/client')
  return { ...actual, generateCalendar: vi.fn() }
})

const mockedGenerateCalendar = vi.mocked(client.generateCalendar)

beforeEach(() => {
  mockedGenerateCalendar.mockReset()
})

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/location/i), 'Portland, OR')
  await user.type(screen.getByLabelText(/calendar length/i), '7')
  await user.click(screen.getByRole('button', { name: /generate/i }))
}

describe('GenerateView', () => {
  it('shows an in-progress indicator while the request is pending', async () => {
    let resolveRequest: (value: CalendarResponse) => void = () => {}
    mockedGenerateCalendar.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )
    const user = userEvent.setup()
    render(<GenerateView />)

    await fillAndSubmit(user)

    expect(screen.getByText(/generating/i)).toBeInTheDocument()

    resolveRequest({
      output_path: 'x.md',
      generated_at: '2026-09-13',
      events: [],
      event_count: 0,
    })
    await waitFor(() => expect(screen.queryByText(/generating/i)).not.toBeInTheDocument())
  })

  it('renders the returned events on success', async () => {
    mockedGenerateCalendar.mockResolvedValue({
      output_path: 'x.md',
      generated_at: '2026-09-13',
      event_count: 1,
      events: [
        {
          name: 'Jazz Night',
          date: '2026-09-20',
          start_time: '20:00',
          venue: 'The Blue Note',
          cost: 'free',
          event_type: 'music',
          genre: 'jazz',
          source_url: 'https://example.com',
        },
      ],
    })
    const user = userEvent.setup()
    render(<GenerateView />)

    await fillAndSubmit(user)

    expect(await screen.findByText('Jazz Night')).toBeInTheDocument()
  })

  it('shows an explicit "no events matched" message when event_count is 0', async () => {
    mockedGenerateCalendar.mockResolvedValue({
      output_path: 'x.md',
      generated_at: '2026-09-13',
      event_count: 0,
      events: [],
    })
    const user = userEvent.setup()
    render(<GenerateView />)

    await fillAndSubmit(user)

    expect(await screen.findByText(/no events matched/i)).toBeInTheDocument()
  })
})

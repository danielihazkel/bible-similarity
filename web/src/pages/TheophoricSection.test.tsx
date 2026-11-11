// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { TheophoricResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import type { Locale } from '../i18n'
import { TheophoricSection } from './TheophoricSection'

const forms = (yahu: number, yah: number, el = 0) => ({ yahu, yah, yeho: 0, yo: 0, el_first: 0, el_last: el })
const DATA: TheophoricResponse = {
  names_total: 2,
  occurrences: 7,
  claim: { early_short: 0.26, late_short: 0.64, difference: 0.38, null_mean: 0.3, p: 0.0531, holds: false, occurrences: 6, names: 12 },
  alpha: 0.05,
  shuffles: 9999,
  known: [
    { books: ['Jer'], book_ids: [23], side: 'long', short: 0.24, endings: 279, holds: true },
    { books: ['1Chr', '2Chr'], book_ids: [37, 38], side: 'short', short: 0.44, endings: 430, holds: false },
  ],
  books: [
    { book_id: 23, ...forms(212, 67) },
    { book_id: 1, ...forms(0, 0) },
  ],
  names: [{ lemma: '3414', he: 'יִרְמְיָה', divine: 'yah', n: 140, ...forms(120, 20) }],
}

function renderIt(locale: Locale = 'en') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(DATA))),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const names = new Map([
    [23, 'Jeremiah'],
    [37, 'I Chronicles'],
    [38, 'II Chronicles'],
  ])
  return render(
    <LocaleProvider initial={locale}>
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <TheophoricSection names={names} />
        </MemoryRouter>
      </QueryClientProvider>
    </LocaleProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('TheophoricSection (DESIGN.md §16.90, D152)', () => {
  it('states the claim, the books named in advance, the forms by book and the names', async () => {
    renderIt()
    expect(await screen.findByRole('heading', { level: 2, name: 'Names built on God’s name' })).toBeTruthy()
    expect(screen.getByText('Not borne out')).toBeTruthy()
    expect(screen.getByText(/the late books .* spell the ending short 64% of the time, Genesis–Kings 26% \(12 names in both; p 0\.053/)).toBeTruthy()
    const known = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(known).toEqual([
      'Jeremiah: mostly long (‑יהו): 24% short of 279 endings · holds',
      'I Chronicles, II Chronicles: mostly short (‑יה): 44% short of 430 endings · does not hold',
    ])
    // a book without such names is left out of the table
    const rows = screen.getAllByRole('row').map((r) => r.textContent)
    expect(rows[1]).toBe('Jeremiah2126724%000')
    expect(rows).toHaveLength(4) // the two heads, Jeremiah, Jeremiah's name
    expect(screen.getByRole('link', { name: 'יִרְמְיָה' }).getAttribute('href')).toBe('/names?e=3414')
    expect(screen.getByText('‑יהו 120× · ‑יה 20×')).toBeTruthy()
  })

  it('is in Hebrew with the Hebrew interface', async () => {
    renderIt('he')
    expect(await screen.findByRole('heading', { level: 2, name: 'שמות הבנויים על שם האל' })).toBeTruthy()
    expect(screen.getByText('לא מתאשר')).toBeTruthy()
  })
})

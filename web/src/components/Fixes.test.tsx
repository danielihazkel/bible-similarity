// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Verse } from '../api/types'
import { TextModeProvider } from '../context/TextMode'
import { ExportCsv } from './ExportCsv'
import { HebrewText } from './HebrewText'
import { Layout } from './Layout'
import { EmptyList, Pager } from './Pager'

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

afterEach(cleanup)

describe('Pager', () => {
  it('jumps to a typed page, clamped to the range', () => {
    const onPage = vi.fn()
    render(<Pager page={2} pages={9} onPage={onPage} />)
    const box = screen.getByLabelText('Page (of 9)')
    expect(box.getAttribute('aria-current')).toBe('page')
    fireEvent.change(box, { target: { value: '40' } })
    fireEvent.click(screen.getByRole('button', { name: 'Go' }))
    expect(onPage).toHaveBeenCalledWith(9)
  })

  it('offers the last page when the URL points past the end', async () => {
    render(
      <MemoryRouter initialEntries={['/x?page=999']}>
        <Routes>
          <Route
            path="/x"
            element={
              <EmptyList total={120} limit={50}>
                Nothing.
              </EmptyList>
            }
          />
        </Routes>
        <Location />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Page 999 is past the end of this list \(3 pages\)/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Go to the last page' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/x?page=3'))
  })

  it('keeps the list message when the list is empty', () => {
    render(
      <MemoryRouter>
        <EmptyList total={0} limit={50}>
          Nothing matches.
        </EmptyList>
      </MemoryRouter>,
    )
    expect(screen.getByText('Nothing matches.')).toBeTruthy()
  })
})

describe('ExportCsv', () => {
  it('links the full export with the filters but not the page', () => {
    render(<ExportCsv filename="x.csv" rows={() => []} all={{ list: 'phrases', params: { book: 3, limit: 50, offset: 100 } }} />)
    expect(screen.getByRole('link', { name: 'Export all (CSV)' }).getAttribute('href')).toBe('/api/export/phrases.csv?book=3')
  })
})

describe('HebrewText', () => {
  it('is one tab stop per verse; arrow keys move between words', () => {
    const v: Verse = { verse_id: 0, book_id: 0, chapter: 1, verse: 1, ref: 'x', ref_he: 'הפניה', text_display: '', display_tokens: ['א', 'ב', 'ג'], ketiv_note: null }
    render(
      <TextModeProvider>
        <HebrewText verse={v} onWordClick={() => {}} />
      </TextModeProvider>,
    )
    const words = screen.getAllByRole('button')
    expect(words.map((w) => w.tabIndex)).toEqual([0, -1, -1])
    words[0].focus()
    fireEvent.keyDown(words[0], { key: 'ArrowLeft' }) // next word in right-to-left reading
    expect(document.activeElement).toBe(words[1])
    fireEvent.keyDown(words[1], { key: 'End' })
    expect(document.activeElement).toBe(words[2])
  })
})

describe('Layout accessibility', () => {
  it('has a skip link, a copy-link button, and titles the page after its heading', async () => {
    render(
      <TextModeProvider>
        <MemoryRouter initialEntries={['/a']}>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/a" element={<h1>First page</h1>} />
              <Route path="/b" element={<h1>Second page</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </TextModeProvider>,
    )
    expect(screen.getByRole('link', { name: 'Skip to content' }).getAttribute('href')).toBe('#main')
    await waitFor(() => expect(document.title).toBe('First page · Tanakh Similarity'))
    expect(screen.getByRole('button', { name: /Copy link/ })).toBeTruthy()
  })
})

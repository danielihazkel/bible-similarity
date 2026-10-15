// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type {
  GematriaFormsResponse,
  GematriaLemmasResponse,
  GematriaResponse,
  GematriaValueResponse,
  GematriaVersesResponse,
  Verse,
} from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { GematriaPage } from './GematriaPage'

const KNOWN = [
  { text: 'אליעזר', value: 318 },
  { text: 'נחש', value: 358 },
]
const values = (standard: number) => ({ standard, gadol: standard, ordinal: 66, katan: 21 })
const verse: Verse = {
  verse_id: 0,
  book_id: 0,
  chapter: 1,
  verse: 1,
  ref: 'Genesis 1:1',
  ref_he: 'בראשית א:א',
  text_display: 'בְּרֵאשִׁית בָּרָא',
  display_tokens: ['בְּרֵאשִׁית', 'בָּרָא'],
  ketiv_note: null,
}

function summary(value: number, system: string, computed = true): GematriaResponse {
  return { computed, value, system: system as GematriaResponse['system'], forms: 65, words: 675, lemmas: 17, verses: 1, known: KNOWN }
}
const page = { total: 1, offset: 0, limit: 25 }
const FORMS = (value: number): GematriaFormsResponse => ({
  value,
  system: 'standard',
  ...page,
  items: [{ form: 'וישב', values: values(318), n_words: 239, n_verses: 228, verses: [{ verse_id: 95, label_en: 'Genesis 4:16', label_he: 'בראשית ד:טז' }] }],
})
const LEMMAS: GematriaLemmasResponse = {
  value: 318,
  system: 'standard',
  ...page,
  items: [{ lemma: '461', he: 'אֱלִיעֶזֶר', values: values(318), n_words: 14 }],
}
const VERSES: GematriaVersesResponse = {
  value: 318,
  system: 'standard',
  book: null,
  ...page,
  items: [{ verse, label_en: 'Genesis 1:1', label_he: 'בראשית א:א', values: values(318), n_letters: 9, n_words: 2 }],
}

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', computed = true) {
  const calls: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      calls.push(url)
      const u = new URL(url, 'http://x')
      const value = Number(u.searchParams.get('value'))
      const system = u.searchParams.get('system') ?? 'standard'
      const text = u.searchParams.get('text') ?? ''
      const valueOf: GematriaValueResponse = { text, letters: text.replace(/[^א-ת]/g, ''), values: { standard: 318, gadol: 318, ordinal: 66, katan: 21 } }
      const body =
        u.pathname === '/api/books'
          ? []
          : u.pathname === '/api/gematria'
            ? summary(value, system, computed)
            : u.pathname === '/api/gematria/value'
              ? valueOf
              : u.pathname === '/api/gematria/forms'
                ? FORMS(value)
                : u.pathname === '/api/gematria/lemmas'
                  ? LEMMAS
                  : u.pathname === '/api/gematria/verses'
                    ? VERSES
                    : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const r = render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/gematria" element={<GematriaPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
  return { ...r, calls }
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('GematriaPage', () => {
  it('values a word in each system and lists the forms of the same value', async () => {
    const { calls } = renderAt('/gematria?q=%D7%90%D7%9C%D7%99%D7%A2%D7%96%D7%A8')
    expect(await screen.findByText(/The value of אליעזר in each system/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Ordinal 66/ })).toBeTruthy()
    expect(await screen.findByText(/318 \(Standard\): 65 written forms \(675 words in the text\), 17 lemmas and 1 verse\./)).toBeTruthy()
    expect(await screen.findByText('וישב')).toBeTruthy()
    expect(screen.getByText(/239 times in 228 verses/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Genesis 4:16' }).getAttribute('href')).toBe('/unit/v%3A95')
    expect(calls.some((c) => c.includes('/api/gematria/forms?value=318&system=standard'))).toBe(true)
  })

  it('takes a number, switches system and view through the URL', async () => {
    renderAt('/gematria?q=318')
    expect(await screen.findByText(/318 \(Standard\)/)).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Lemmas (17)' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/gematria?q=318&view=lemmas'))
    const chip = await screen.findByRole('link', { name: /אֱלִיעֶזֶר/ })
    expect(chip.getAttribute('href')).toBe('/lemma/461')
    fireEvent.click(screen.getByRole('radio', { name: 'Verses (1)' }))
    expect(await screen.findByText(/9 letters, 2 words/)).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Large' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/gematria?q=318&view=verses&system=gadol'))
    expect(await screen.findByText(/318 \(Large\)/)).toBeTruthy()
  })

  it('fills the box from a traditional equivalence and updates the URL', async () => {
    renderAt('/gematria')
    fireEvent.click(await screen.findByRole('button', { name: /נחש 358/ }))
    expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('נחש')
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/gematria?q=%D7%A0%D7%97%D7%A9'))
  })

  it('asks for Hebrew letters or a number', async () => {
    renderAt('/gematria?q=abc')
    expect(await screen.findByText('Type Hebrew letters or a number.')).toBeTruthy()
  })

  it('says when the build has no gematria', async () => {
    renderAt('/gematria?q=318', 'en', false)
    expect(await screen.findByText(/Not computed in this build: run `bsim gematria`/)).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    renderAt('/gematria?q=318', 'he')
    expect(await screen.findByRole('heading', { name: 'גימטריה' })).toBeTruthy()
    expect(await screen.findByText(/318 \(רגיל\)/)).toBeTruthy()
    expect(screen.getByRole('radio', { name: 'גדול' })).toBeTruthy()
  })
})

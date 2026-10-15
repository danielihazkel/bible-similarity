// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Book, MasorahMiddle, MasorahResponse, Verse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { MasorahPage } from './MasorahPage'

const verse = (verse_id: number, ref: string, ref_he: string, tokens: string[]): Verse => ({
  verse_id,
  book_id: 2,
  chapter: Number(ref.split(' ')[1].split(':')[0]),
  verse: Number(ref.split(':')[1]),
  ref,
  ref_he,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const LEV_11_42 = verse(3036, 'Leviticus 11:42', 'ויקרא יא:מב', ['כֹּל֩', 'הוֹלֵ֨ךְ', 'עַל־', 'גָּח֜וֹן'])
const LEV_8_28 = verse(2942, 'Leviticus 8:28', 'ויקרא ח:כח', ['וַיִּקַּ֨ח', 'מֹשֶׁ֤ה', 'לַֽיהוָֽה׃'])
const LEV_8_8 = verse(2922, 'Leviticus 8:8', 'ויקרא ח:ח', ['וַיָּ֥שֶׂם', 'עָלָ֖יו'])
const letter = (text: 'ketiv' | 'qere', n: number, distance: number): MasorahMiddle => ({
  claim: 0,
  span: 'Torah',
  unit: 'letter',
  text,
  source: 'talmud',
  holds: false,
  trad_verse: LEV_11_42,
  trad_tok: 3,
  trad_word: 'גחון',
  trad_letter: 3,
  mid_verse: LEV_8_28,
  mid_tok: 2,
  mid_word: 'ליהוה',
  mid_letter: 1,
  n,
  trad_pos: 157229,
  mid_pos: (n - 1) / 2,
  distance,
  verses_apart: 94,
})
const DATA: MasorahResponse = {
  meta: {
    tolerance: 1,
    text: 'ketiv',
    kq: { pairs: 1260, changed: { ketiv: 1036, qere: 237 }, unaligned: 1 },
    torah: { verses: 5846, words_ketiv: 79978, words_qere: 79980, letters_ketiv: 304801, letters_qere: 304830 },
    checks: { letter: { ref: 'Leviticus 11:42', n: 304801, distance: 4829, verses_apart: 94, holds: false } },
  },
  middles: [
    letter('ketiv', 304801, 4829),
    letter('qere', 304830, 4824.5),
    {
      claim: 2,
      span: 'Torah',
      unit: 'verse',
      text: null,
      source: 'masorah',
      holds: true,
      trad_verse: LEV_8_8,
      trad_tok: null,
      trad_word: null,
      trad_letter: null,
      mid_verse: LEV_8_8,
      mid_tok: null,
      mid_word: null,
      mid_letter: null,
      n: 5846,
      trad_pos: 2922,
      mid_pos: 2922.5,
      distance: -0.5,
      verses_apart: 0,
    },
  ],
  totals: [
    {
      scope: 'book',
      name: null,
      first_book: 1,
      last_book: 1,
      unit: 'verses',
      text: null,
      source: 'masorah',
      tradition: 1209,
      ours: 1210,
      diff: 1,
      book_sum: null,
      reason: 'decalogue',
      ref_first: { verse_id: 2053, label_en: 'Exodus 20:2', label_he: 'שמות כ:ב' },
      ref_last: { verse_id: 2065, label_en: 'Exodus 20:14', label_he: 'שמות כ:יד' },
      also: [],
    },
    {
      scope: 'book',
      name: 'kings',
      first_book: 9,
      last_book: 10,
      unit: 'verses',
      text: null,
      source: 'masorah',
      tradition: 1534,
      ours: 1534,
      diff: 0,
      book_sum: null,
      reason: null,
      ref_first: null,
      ref_last: null,
      also: [1536],
    },
    {
      scope: 'section',
      name: 'torah',
      first_book: 0,
      last_book: 4,
      unit: 'letters',
      text: 'ketiv',
      source: 'printed',
      tradition: 304805,
      ours: 304801,
      diff: -4,
      book_sum: null,
      reason: null,
      ref_first: null,
      ref_last: null,
      also: [],
    },
  ],
  books: [{ book_id: 1, verses: 1210, words_ketiv: 16713, words_qere: 16713, letters_ketiv: 63529, letters_qere: 63535 }],
}
const BOOKS = [{ book_id: 1, name: 'Exodus', he_name: 'שמות', osis: 'Exod', section: 'Torah', n_chapters: 40 }] as Book[]

function Location() {
  const l = useLocation()
  return <output data-testid="loc">{l.pathname + l.search}</output>
}

function renderAt(path: string, locale: 'en' | 'he' = 'en', data: MasorahResponse = DATA) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      const p = new URL(url, 'http://x').pathname
      const body = p === '/api/books' ? BOOKS : p === '/api/masorah' ? data : null
      return new Response(JSON.stringify(body ?? { detail: 'nope' }), { status: body ? 200 : 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/masorah" element={<MasorahPage />} />
          </Routes>
          <Location />
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('MasorahPage', () => {
  it('says where each middle the tradition names falls against ours', async () => {
    const { container } = renderAt('/masorah')
    expect(await screen.findByText(/the Torah has 5,846 verses: as written, 79,978 words and 304,801 letters/)).toBeTruthy()
    const items = container.querySelectorAll('.msr-middle')
    expect(items).toHaveLength(2)
    expect(items[0].textContent).toContain('According to Kiddushin 30a: the 3rd letter of גחון')
    expect(items[0].textContent).toContain('the 1st letter of ליהוה')
    expect(items[0].textContent).toContain('letter 152,401 of 304,801')
    expect(items[0].textContent).toContain('It falls 4,829 letters after ours, 94 verses on.')
    expect(items[1].textContent).toContain('between verse 2,923 and 2,924 of 5,846')
    expect(items[1].textContent).toContain('It falls 0.5 verses before ours.')
    expect([...container.querySelectorAll('.dlg-verdict')].map((v) => v.textContent)).toEqual(['off', 'lands'])
    // the tradition's word and ours marked in their verses
    expect(items[0].querySelectorAll('.w-focus')).toHaveLength(2)
  })

  it('switches to the letters as read', async () => {
    const { container } = renderAt('/masorah')
    fireEvent.click(await screen.findByRole('radio', { name: 'As read' }))
    await waitFor(() => expect(screen.getByTestId('loc').textContent).toBe('/masorah?text=qere'))
    expect(container.querySelector('.msr-middle')?.textContent).toContain('It falls 4,824.5 letters after ours')
  })

  it('lists the verse totals with the reason a book differs', async () => {
    const { container } = renderAt('/masorah')
    const exodus = await screen.findByRole('link', { name: 'Exodus 20:2–14' })
    expect(exodus.getAttribute('href')).toBe('/unit/v%3A2053')
    const rows = container.querySelectorAll('.msr-totals tbody tr')
    expect(rows[0].textContent).toContain('The Ten Commandments are divided otherwise')
    expect(rows[0].textContent).toContain('+1')
    expect(rows[1].textContent).toContain('Kings')
    expect(rows[1].textContent).toContain('agrees')
    expect(rows[1].textContent).toContain('1,536')
    expect(screen.getByText('1 of 2 books have the Masorah’s total.')).toBeTruthy()
    expect(screen.getByText('Letters (as written)')).toBeTruthy()
    expect(screen.getByText('−4')).toBeTruthy()
  })

  it('says when the build has no counts', async () => {
    renderAt('/masorah', 'en', { meta: {}, middles: [], totals: [], books: [] })
    expect(await screen.findByText(/Not computed in this build: run `bsim masorah`/)).toBeTruthy()
  })

  it('reads in Hebrew', async () => {
    const { container } = renderAt('/masorah', 'he')
    expect(await screen.findByRole('heading', { name: 'מניין המסורה' })).toBeTruthy()
    await waitFor(() => expect(container.querySelector('.msr-middle')?.textContent).toContain('לפי קידושין ל ע״א: האות ה־3 של גחון'))
    expect(screen.getByRole('link', { name: 'שמות כ:ב–יד' })).toBeTruthy()
  })
})

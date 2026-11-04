// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { SourceExamples, SourceResponse } from '../api/types'
import { LocaleProvider } from '../context/Locale'
import { SourcePage } from './SourcePage'

const verse = (id: number, ref: string, tokens: string[]) => ({
  verse_id: id,
  book_id: 3,
  chapter: 6,
  verse: id,
  ref,
  ref_he: `ה${ref}`,
  text_display: tokens.join(' '),
  display_tokens: tokens,
  ketiv_note: null,
})
const EXAMPLES: SourceExamples = { max_chars: 40, examples: [{ key: 'priestly', text: 'יברכך ה׳ וישמרך' }] }
const FOUND: SourceResponse = {
  tokens: ['אמר', 'יברכך', 'ה׳', 'וישמרך', 'עוד'],
  passages: [
    {
      first: 1,
      last: 3,
      score: 30.5,
      matched: 3,
      verses: [{ verse: verse(24, 'Numbers 6:24', ['יְבָרֶכְךָ', 'יְהוָה', 'וְיִשְׁמְרֶךָ']), tokens: [0, 1, 2], text_tokens: [1, 2, 3] }],
      alternatives: [verse(99, 'Psalms 1:1', ['אשרי'])],
    },
  ],
}

const posts: string[] = []

function renderAt(path: string, locale: 'en' | 'he' = 'en', reply: SourceResponse | 'long' = FOUND) {
  posts.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const p = new URL(url, 'http://x').pathname
      if (p === '/api/source-find/examples') return new Response(JSON.stringify(EXAMPLES), { status: 200 })
      if (p === '/api/source-find' && init?.method === 'POST') {
        posts.push(JSON.parse(String(init.body)).text)
        if (reply === 'long') return new Response(JSON.stringify({ detail: { code: 'too_long', max_chars: 40, message: 'x' } }), { status: 422 })
        return new Response(JSON.stringify(reply), { status: 200 })
      }
      return new Response(JSON.stringify({ detail: 'nope' }), { status: 404 })
    }),
  )
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LocaleProvider initial={locale}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/source" element={<SourcePage />} />
          </Routes>
        </MemoryRouter>
      </LocaleProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('SourcePage', () => {
  it('searches a pasted text and marks its passage, linked to the verse', async () => {
    const { container } = renderAt('/source')
    fireEvent.change(screen.getByLabelText('Hebrew text'), { target: { value: 'אמר יברכך ה׳ וישמרך עוד' } })
    fireEvent.click(screen.getByRole('button', { name: 'Find the sources' }))
    expect(await screen.findByText('1 passage from the Bible, 3 words of the text.')).toBeTruthy()
    expect(posts).toEqual(['אמר יברכך ה׳ וישמרך עוד'])
    // the three words marked in the text, with the passage's number linking to it
    expect([...container.querySelectorAll('.sf-text mark')].map((m) => m.textContent)).toEqual(['יברכך', 'ה׳', 'וישמרך'])
    expect(screen.getByRole('link', { name: 'Passage 1' }).getAttribute('href')).toBe('#sf-p1')
    expect(screen.getByRole('link', { name: 'Numbers 6:24' }).getAttribute('href')).toBe('/unit/v%3A24')
    expect(container.querySelectorAll('.sf-passages .hit-text mark')).toHaveLength(3)
    expect(screen.getByRole('link', { name: 'Psalms 1:1' })).toBeTruthy()
  })

  it('fills and searches an example named in the address', async () => {
    renderAt('/source?example=priestly')
    await waitFor(() => expect(posts).toEqual(['יברכך ה׳ וישמרך']))
    expect((screen.getByLabelText('Hebrew text') as HTMLTextAreaElement).value).toBe('יברכך ה׳ וישמרך')
    expect(screen.getByRole('button', { name: 'The priestly blessing' })).toBeTruthy()
  })

  it('refuses a text longer than the limit, and says when nothing is found', async () => {
    renderAt('/source', 'en', { tokens: ['שלום'], passages: [] })
    await screen.findByText(/of 40 characters/)
    fireEvent.change(screen.getByLabelText('Hebrew text'), { target: { value: 'א'.repeat(41) } })
    expect(screen.getByText('The text is longer than 40 characters; shorten it to search.')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Find the sources' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(screen.getByLabelText('Hebrew text'), { target: { value: 'שלום' } })
    fireEvent.click(screen.getByRole('button', { name: 'Find the sources' }))
    expect(await screen.findByText('No phrase of the Bible was found in this text.')).toBeTruthy()
  })

  it('runs in the Hebrew interface', async () => {
    renderAt('/source', 'he')
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('מאתר המקורות')
    expect(await screen.findByRole('button', { name: 'ברכת כהנים' })).toBeTruthy()
  })
})

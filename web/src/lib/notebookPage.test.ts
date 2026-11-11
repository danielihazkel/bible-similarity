// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import type { NotebookCollection, NotebookEntry, UnitSummary } from '../api/types'
import { studyPage } from './notebookPage'

const unit = (id: string, type: UnitSummary['unit_type'], en: string, he: string): UnitSummary => ({
  unit_id: id,
  unit_type: type,
  label_en: en,
  label_he: he,
  book_id: 0,
  start_verse_id: 0,
  end_verse_id: 0,
  n_verses: 1,
  marker: null,
})
const entry = (u: UnitSummary, note: string, collections: number[], text?: string): NotebookEntry => ({
  unit: u,
  note,
  collections,
  created_at: '',
  updated_at: '',
  verse: text
    ? { verse_id: 0, book_id: 0, chapter: 1, verse: 1, ref: 'Genesis 1:1', ref_he: 'בראשית', text_display: text, display_tokens: text.split(' '), ketiv_note: null }
    : null,
})
const COLS: NotebookCollection[] = [{ collection_id: 1, name: 'Openings', description: 'First words.\n\nAnd <more>.', n_entries: 1, created_at: '', updated_at: '' }]
const T = {
  title: 'Notebook',
  exported: (d: string) => `Exported ${d}.`,
  collections: 'Collections',
  open: 'Open the passage',
  source: 'The verses: Sefaria.',
  madeWith: (s: string) => `Made with it, ${s}`,
}
const ENTRIES = [
  entry(unit('v:0', 'verse', 'Genesis 1:1', 'בראשית א:א'), 'A <b>bold</b> "claim" & more\nsecond line', [1], 'בְּרֵאשִׁ֖ית בָּרָ֣א'),
  entry(unit('c:0:1', 'chapter', 'Genesis 1', 'בראשית א'), '', []),
]

const parse = (html: string) => new DOMParser().parseFromString(html, 'text/html')

describe('the study page (DESIGN.md §16.47, D151)', () => {
  it('is one page: the heading, the day, each passage linked back, the verse, the note, the source', () => {
    const doc = parse(studyPage(ENTRIES, COLS, COLS[0], T, 'en', '2026-11-10', 'http://localhost:8000', 'teamim'))
    expect(doc.documentElement.getAttribute('lang')).toBe('en')
    expect(doc.documentElement.getAttribute('dir')).toBe('ltr')
    expect(doc.title).toBe('Notebook: Openings')
    expect(doc.querySelector('.meta')?.textContent).toBe('Exported 2026-11-10.')
    expect([...doc.querySelectorAll('.desc p')].map((p) => p.textContent)).toEqual(['First words.', 'And <more>.'])
    const links = [...doc.querySelectorAll('h2 a')]
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['http://localhost:8000/unit/v%3A0', 'http://localhost:8000/unit/c%3A0%3A1'])
    expect(links[0].textContent).toBe('Genesis 1:1 בראשית א:א')
    const quote = doc.querySelector('blockquote')!
    expect([quote.getAttribute('lang'), quote.getAttribute('dir'), quote.textContent]).toEqual(['he', 'rtl', 'בְּרֵאשִׁ֖ית בָּרָ֣א'])
    expect(doc.querySelectorAll('blockquote')).toHaveLength(1) // a chapter has no verse text
    // the note is text, never markup: its tags and quotes come through as written
    const note = doc.querySelector('.note p')!
    expect(note.textContent).toBe('A <b>bold</b> "claim" & moresecond line')
    expect(note.querySelector('b')).toBeNull()
    expect(note.innerHTML).toContain('<br>')
    expect(doc.querySelector('.cols')?.textContent).toBe('Collections: Openings')
    expect(doc.querySelector('footer')?.textContent).toContain('The verses: Sefaria.')
  })

  it('takes the text display and the interface language', () => {
    const doc = parse(studyPage(ENTRIES, COLS, undefined, { ...T, title: 'המחברת' }, 'he', 'x', 'https://example.org', 'consonants'))
    expect(doc.documentElement.getAttribute('dir')).toBe('rtl')
    expect(doc.title).toBe('המחברת')
    expect(doc.querySelector('blockquote')?.textContent).toBe('בראשית ברא')
    expect(doc.querySelector('h2 a')?.textContent).toBe('בראשית א:א')
    expect(doc.querySelector('.desc')).toBeNull()
  })
})

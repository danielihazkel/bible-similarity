import { describe, expect, it } from 'vitest'
import type { DossierEntry, UnitSummary } from '../api/types'
import { entryLink, isFound } from './dossier'

const entry = (e: Partial<DossierEntry>): DossierEntry => ({
  kind: 'gematria', scope: 'unit', computed: true, count: 0, total: null, value: null, key: null, label: null, target_unit: null, ...e,
})  // prettier-ignore
const unit = (unit_id: string, unit_type: string): UnitSummary => ({
  unit_id, unit_type, label_en: unit_id, label_he: unit_id, book_id: 0, start_verse_id: 0, end_verse_id: 9, n_verses: 10, marker: null,
}) as UnitSummary  // prettier-ignore

describe('the dossier', () => {
  it('counts a verse’s letter value as found, and a passage’s only with the tradition’s texts', () => {
    expect(isFound(entry({ value: 2701, total: 0 }))).toBe(true)
    expect(isFound(entry({}))).toBe(false)
    expect(isFound(entry({ count: 3, label: 'נחש' }))).toBe(true)
    expect(isFound(entry({ computed: false, value: 2701 }))).toBe(false)
  })

  it('links a verse to the verses of its value and a passage to the reader', () => {
    expect(entryLink(entry({ value: 2701 }), unit('v:0', 'verse'))).toBe('/gematria?q=2701&view=verses')
    expect(entryLink(entry({ count: 5 }), unit('c:0:3', 'chapter'))).toBe('/read/c%3A0%3A3?layers=gematria')
    expect(entryLink(entry({ kind: 'places', count: 2 }), unit('c:0:3', 'chapter'))).toBe('/places?unit=c%3A0%3A3')
    expect(entryLink(entry({ kind: 'ciphers', count: 1 }), unit('c:23:25', 'chapter'))).toBe('/ciphers?unit=c%3A23%3A25')
    expect(entryLink(entry({ kind: 'people', count: 4, key: '17' }), unit('v:0', 'verse'))).toBe('/genealogy?p=17')
  })
})

import { describe, expect, it } from 'vitest'
import type { DossierEntry, DossierKind, UnitSummary } from '../api/types'
import { dosEn } from '../i18n/pages/dossier'
import { entryFamily, entryLink, families, isFound } from './dossier'

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
    expect(entryLink(entry({ kind: 'divine', count: 4, key: 'elohim', value: 0.2 }), unit('c:26:53', 'chapter'))).toBe('/read/c%3A26%3A53?layers=divine')
    expect(entryLink(entry({ kind: 'people', count: 4, key: '17' }), unit('v:0', 'verse'))).toBe('/genealogy?p=17')
  })

  it('puts a finding in the family of the nav page it is read on', () => {
    const verse = unit('v:0', 'verse')
    const chapter = unit('c:0:3', 'chapter')
    expect(entryFamily(entry({ kind: 'phrases', count: 1 }), verse)).toEqual({ group: 'parallels' })
    expect(entryFamily(entry({ kind: 'ketiv', count: 1 }), verse)).toEqual({ group: 'patterns', section: 'wordsNames' })
    expect(entryFamily(entry({ kind: 'reception', count: 1 }), verse)).toEqual({ group: 'patterns', section: 'narrative' })
    expect(entryFamily(entry({ kind: 'people', count: 1, key: '17' }), verse)).toEqual({ group: 'overview' })
    // read on the unit page or in the reader: the page of its analysis
    expect(entryFamily(entry({ kind: 'acrostic', count: 1, value: 0.01 }), chapter)).toEqual({ group: 'patterns', section: 'poetryForm' })
    expect(entryFamily(entry({ kind: 'divine', count: 4 }), chapter)).toEqual({ group: 'patterns', section: 'wordsNames' })
    expect(entryFamily(entry({ count: 5 }), chapter)).toEqual({ group: 'patterns', section: 'lettersNumbers' })
    expect(entryFamily(entry({ kind: 'names', count: 2 }), verse)).toEqual({ group: 'patterns', section: 'wordsNames' })
  })

  it('has a family for every kind of finding, on a verse and on a chapter', () => {
    for (const kind of Object.keys(dosEn.kinds) as DossierKind[])
      for (const u of [unit('v:0', 'verse'), unit('c:0:3', 'chapter')]) expect(entryFamily(entry({ kind, count: 1 }), u).group, `${kind} on a ${u.unit_type}`).toBeDefined()
  })

  it('lists the families in the nav’s order, the findings in the dossier’s own', () => {
    const got = families(
      [entry({ kind: 'people', count: 1 }), entry({ kind: 'roots', count: 1 }), entry({ kind: 'phrases', count: 1 }), entry({ kind: 'places', count: 1 }), entry({ kind: 'changes', count: 1 })],
      unit('v:0', 'verse'),
    )
    expect(got.map((f) => [f.section ?? f.group, f.entries.map((e) => e.kind)])).toEqual([
      ['parallels', ['phrases', 'changes']],
      ['wordsNames', ['roots']],
      ['overview', ['people', 'places']],
    ])
  })
})

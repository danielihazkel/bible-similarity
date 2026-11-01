import { describe, expect, it } from 'vitest'
import { hebrewNumeral } from '../lib/hebrew'
import { en } from './en'
import { he } from './he'

/** Every leaf of a catalog as [path, value]. */
function leaves(o: unknown, path = ''): [string, unknown][] {
  if (o && typeof o === 'object' && !Array.isArray(o))
    return Object.entries(o).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k))
  return [[path, o]]
}

describe('catalogs', () => {
  const enLeaves = new Map(leaves(en))
  const heLeaves = new Map(leaves(he))

  it('have the same keys, kinds and function arities', () => {
    expect([...heLeaves.keys()].sort()).toEqual([...enLeaves.keys()].sort())
    for (const [k, v] of enLeaves) {
      const h = heLeaves.get(k)
      expect(typeof h, k).toBe(typeof v)
      if (typeof v === 'function') expect((h as (...a: unknown[]) => unknown).length, k).toBe(v.length)
    }
  })

  it('have no empty strings', () => {
    for (const [k, v] of [...enLeaves, ...heLeaves]) if (typeof v === 'string') expect(v.trim(), k).not.toBe('')
  })

  it('count in Hebrew with one, two and many', () => {
    expect(he.units.verses(1)).toBe('פסוק אחד')
    expect(he.units.verses(2)).toBe('שני פסוקים')
    expect(he.units.verses(1234)).toBe('1,234 פסוקים')
    expect(en.units.verses(1)).toBe('1 verse')
    expect(en.units.verses(1234)).toBe('1,234 verses')
  })

  it('agree on gendered unit phrases and references', () => {
    expect(he.unit.similarOf('parasha')).toBe('פרשות דומות')
    expect(en.unit.similarOf('parasha')).toBe('Similar parashot')
    expect(en.unit.network(3, 929, 'chapter', 12, 0.4)).toContain('3rd most echoed of 929 chapters')
    expect(he.cv(15, 16)).toBe('טו:טז')
    expect(en.cv(15, 16)).toBe('15:16')
  })
})

describe('hebrewNumeral', () => {
  it('writes gematria like the server', () => {
    expect(hebrewNumeral(1)).toBe('א')
    expect(hebrewNumeral(15)).toBe('טו')
    expect(hebrewNumeral(16)).toBe('טז')
    expect(hebrewNumeral(119)).toBe('קיט')
    expect(hebrewNumeral(150)).toBe('קנ')
    expect(hebrewNumeral(0)).toBe('0')
  })
})

describe('the Hebrew catalog loads on demand', () => {
  it('no English-side module imports it statically', () => {
    const sources = import.meta.glob(['./en.ts', './index.ts', './pages/*.ts'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>
    expect(Object.keys(sources).length).toBeGreaterThan(40)
    for (const [f, src] of Object.entries(sources)) {
      expect(src, f).not.toMatch(/from '\.\/he'|from '\.\.\/he'|from '\.\/pages\/he\/|from '\.\/he\//)
    }
  })

  it('loads Hebrew once and keeps English loaded', async () => {
    const { catalogOf, loadCatalog } = await import('./index')
    expect(catalogOf('en')).toBe(en)
    expect(await loadCatalog('he')).toBe(he)
    expect(catalogOf('he')).toBe(he)
  })
})

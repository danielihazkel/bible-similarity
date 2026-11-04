import { describe, expect, it } from 'vitest'

// The English page groups load with the modules that read them (en.ts `register`, M145): a module
// reading `m.<group>` (or `useT().<group>`) must import that group's file, by a value or a bare
// import (`import type` is erased, so it loads nothing), or the group may not be there when it
// renders. tsc cannot see this; this test reads the sources.
const SOURCES = import.meta.glob(['../**/*.ts', '../**/*.tsx', '!../i18n/**'], {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>
const EN = (import.meta.glob('./en.ts', { query: '?raw', import: 'default', eager: true }) as Record<string, string>)['./en.ts']
const PAGES = import.meta.glob('./pages/*.ts', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

/** group key -> its file stem under pages/, from en.ts's `Groups` and its type imports. */
function groupFiles(): Map<string, string> {
  const fileOf = new Map<string, string>()
  for (const [, names, stem] of EN.matchAll(/^import type \{ ([^}]+) \} from '\.\/pages\/(\w+)'$/gm))
    for (const n of names.split(',')) fileOf.set(n.trim(), stem)
  const body = EN.slice(EN.indexOf('export interface Groups {'))
  const out = new Map<string, string>()
  for (const [, key, name] of body.slice(0, body.indexOf('}')).matchAll(/^ {2}(\w+): typeof (\w+)$/gm)) out.set(key, fileOf.get(name)!)
  return out
}

/** Whether `text` loads `pages/<stem>` at run time: a bare import or one of values. */
const loads = (text: string, stem: string) =>
  new RegExp(String.raw`^import (?!type\b)(?:[^'\n]*from )?'[./]*i18n/pages/` + stem + `'`, 'm').test(text)

describe('catalog groups', () => {
  const groups = groupFiles()

  it('are read from en.ts, and each registers itself', () => {
    expect(groups.size).toBeGreaterThan(40)
    expect(groups.get('lab')).toBe('labels')
    for (const [key, stem] of groups) expect(PAGES[`./pages/${stem}.ts`], `${stem}.ts registers ${key}`).toContain(`register('${key}', `)
  })

  it('are loaded by every module that reads them', () => {
    expect(Object.keys(SOURCES).length).toBeGreaterThan(100)
    const keys = [...groups.keys()].sort((a, b) => b.length - a.length).join('|')
    const use = new RegExp(String.raw`(?:\bm|useT\(\))\.(` + keys + String.raw`)\b`, 'g')
    const missing: string[] = []
    for (const [path, text] of Object.entries(SOURCES))
      for (const key of new Set([...text.matchAll(use)].map((x) => x[1]))) {
        const stem = groups.get(key)!
        if (!loads(text, stem)) missing.push(`${path}: m.${key} (pages/${stem})`)
      }
    expect(missing).toEqual([])
  })

  it('tell a loading import from an erased one', () => {
    expect(loads("import '../i18n/pages/labels'\n", 'labels')).toBe(true)
    expect(loads("import { labEn } from '../i18n/pages/labels'\n", 'labels')).toBe(true)
    expect(loads("import type { TermKey } from '../i18n/pages/glossary'\n", 'glossary')).toBe(false)
  })
})

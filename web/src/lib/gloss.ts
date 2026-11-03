// Terms of the glossary found in running text (DESIGN.md §11): which to mark, and where.
import type { TermKey } from '../i18n/pages/glossary'

export type Patterns = readonly (readonly [string, TermKey])[]

/** The first match of each term in a text, in text order, not overlapping. */
export function matches(text: string, patterns: Patterns, keys: ReadonlySet<TermKey>) {
  const found: { start: number; end: number; key: TermKey }[] = []
  for (const [src, key] of patterns) {
    if (!keys.has(key) || found.some((f) => f.key === key)) continue
    const m = new RegExp(src, 'u').exec(text)
    if (m) found.push({ start: m.index, end: m.index + m[0].length, key })
  }
  found.sort((a, b) => a.start - b.start)
  return found.filter((f, i) => i === 0 || f.start >= found[i - 1].end)
}

/** For texts shown on one page in order: the terms each is the first to use, so that a term is
 * marked once a page (one tab stop each) however often the texts repeat it. */
export function firstUses(texts: string[], patterns: Patterns): Set<TermKey>[] {
  const seen = new Set<TermKey>()
  const all = new Set(patterns.map(([, k]) => k))
  return texts.map((text) => {
    const mine = new Set<TermKey>()
    for (const f of matches(text, patterns, all)) {
      if (!seen.has(f.key)) {
        seen.add(f.key)
        mine.add(f.key)
      }
    }
    return mine
  })
}

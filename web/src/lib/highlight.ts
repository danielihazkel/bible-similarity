import type { ExplainResponse, WordRef } from '../api/types'

export type Mark = 'shared' | 'formula' | 'focus'
export type Highlight = Map<number, Mark>

/**
 * Display-token highlights for one side of an `/explain` result. A token is `formula` when every
 * shared word on it lies inside a formula; words without a display alignment are skipped.
 */
export function highlightFor(explain: ExplainResponse | undefined, side: 'a' | 'b', lemma?: string): Highlight {
  const marks: Highlight = new Map()
  if (!explain) return marks
  for (const s of explain.shared) {
    const words: WordRef[] = side === 'a' ? s.a_words : s.b_words
    for (const w of words) {
      if (w.display_idx === null) continue
      const mark: Mark = lemma === s.lemma ? 'focus' : w.in_formula ? 'formula' : 'shared'
      const prev = marks.get(w.display_idx)
      // focus > shared > formula when several lemmas share a token (prefix + noun etc.)
      if (prev === 'focus' || (prev === 'shared' && mark === 'formula')) continue
      marks.set(w.display_idx, mark)
    }
  }
  return marks
}

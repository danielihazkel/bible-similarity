import type { ExplainResponse, LemmaForm } from '../api/types'
import { useT } from '../context/localeContext'
import { HebrewPlain } from './HebrewText'

interface Props {
  explain?: ExplainResponse
  /** compare pairs carry lemmas without word positions */
  lemmas?: LemmaForm[]
  loading?: boolean
  focus?: string
  onFocus?: (lemma: string | undefined) => void
}

/** Shared lemmas of two verses (`/explain`); formula-only lemmas are dimmed. */
export function LemmaChips({ explain, lemmas, loading, focus, onFocus }: Props) {
  const m = useT()
  const items = explain
    ? explain.shared.map((s) => ({ lemma: s.lemma, he: s.he_lemma, formula: s.formula }))
    : (lemmas ?? []).map((s) => ({ lemma: s.lemma, he: s.he_lemma, formula: false }))
  if (loading && !items.length) return <p className="chips muted">{m.lemmas.finding}</p>
  if (!items.length) return <p className="chips muted">{m.lemmas.none}</p>
  return (
    <div className="chips" aria-label={m.lemmas.shared}>
      <span className="chips-label">{m.lemmas.shared}</span>
      {items.map((s) => (
        <button
          key={s.lemma}
          type="button"
          className={`chip ${s.formula ? 'formula' : ''} ${focus === s.lemma ? 'on' : ''}`}
          title={m.lemmas.strongs(s.lemma, s.formula)}
          onMouseEnter={() => onFocus?.(s.lemma)}
          onMouseLeave={() => onFocus?.(undefined)}
          onFocus={() => onFocus?.(s.lemma)}
          onBlur={() => onFocus?.(undefined)}
        >
          <HebrewPlain text={s.he} />
        </button>
      ))}
    </div>
  )
}

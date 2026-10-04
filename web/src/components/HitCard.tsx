import { Link } from 'react-router'
import type { ExplainResponse, Hit, Mode, UnitSummary } from '../api/types'
import { highlightFor } from '../lib/highlight'
import { compareLink, unitLink } from '../lib/links'
import { HebrewPlain, HebrewText } from './HebrewText'
import { LemmaChips } from './LemmaChips'
import { ScoreBreakdown } from './ScoreBreakdown'

interface Props {
  hit: Hit
  mode: Mode
  source: UnitSummary
  /** Verse hits: this card is the one being explained (hovered or pinned). */
  active?: boolean
  pinned?: boolean
  explain?: ExplainResponse
  explainLoading?: boolean
  focusLemma?: string
  onHover?: (on: boolean) => void
  onTogglePin?: () => void
  onFocusLemma?: (lemma: string | undefined) => void
}

export function HitCard(p: Props) {
  const { hit, mode, source } = p
  const isVerse = hit.verse !== null
  const explain = p.active ? p.explain : undefined
  return (
    <li
      className={`hit ${p.active ? 'active' : ''} ${p.pinned ? 'pinned' : ''}`}
      onMouseEnter={isVerse ? () => p.onHover?.(true) : undefined}
      onMouseLeave={isVerse ? () => p.onHover?.(false) : undefined}
    >
      <div className="hit-head">
        <span className="hit-rank">{hit.rank}</span>
        <Link className="hit-ref" to={unitLink(hit.unit.unit_id)}>
          {hit.unit.label_en}
          <span className="he-label" dir="rtl" lang="he">
            {hit.unit.label_he}
          </span>
        </Link>
        <ScoreBreakdown hit={hit} mode={mode} />
        <span className="hit-actions">
          {isVerse && (
            <button
              type="button"
              className="linkish"
              aria-pressed={p.pinned}
              onClick={p.onTogglePin}
              title="Keep the shared words highlighted"
            >
              {p.pinned ? 'Unpin' : 'Shared words'}
            </button>
          )}
          <Link className="linkish" to={compareLink(source.unit_id, hit.unit.unit_id)} title="Side-by-side comparison">
            Compare
          </Link>
        </span>
      </div>
      {hit.verse ? (
        <p className="hit-text">
          <HebrewText verse={hit.verse} highlight={highlightFor(explain, 'b', p.focusLemma)} />
        </p>
      ) : (
        hit.preview && (
          <p className="hit-text preview">
            <HebrewPlain text={hit.preview} />
            {hit.unit.n_verses > 1 && <span className="muted"> … ({hit.unit.n_verses} verses)</span>}
          </p>
        )
      )}
      {p.active && isVerse && (
        <LemmaChips explain={explain} loading={p.explainLoading} focus={p.focusLemma} onFocus={p.onFocusLemma} />
      )}
    </li>
  )
}

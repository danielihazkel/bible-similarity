import { Link } from 'react-router'
import type { ExplainResponse, Hit, Mode, UnitSummary, VerseDiff } from '../api/types'
import { diffHighlight, highlightFor } from '../lib/highlight'
import { useT } from '../context/localeContext'
import { DiffLegend } from './DiffLegend'
import { compareLink, unitLink } from '../lib/links'
import { HebrewPlain, HebrewText } from './HebrewText'
import { LemmaChips } from './LemmaChips'
import { LinkBadge } from './LinkBadge'
import { ScoreBreakdown } from './ScoreBreakdown'
import { UnitName } from './UnitName'

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
  /** Mark the word-level changes from the source verse (`diff`) instead of the shared words. */
  marks?: 'shared' | 'changes'
  diff?: VerseDiff
}

export function HitCard(p: Props) {
  const m = useT()
  const { hit, mode, source } = p
  const isVerse = hit.verse !== null
  const explain = p.active ? p.explain : undefined
  const changes = p.marks === 'changes'
  const highlight = changes
    ? p.active
      ? diffHighlight(p.diff?.b_marks)
      : undefined
    : highlightFor(explain, 'b', p.focusLemma)
  return (
    <li
      className={`hit ${p.active ? 'active' : ''} ${p.pinned ? 'pinned' : ''}`}
      onMouseEnter={isVerse ? () => p.onHover?.(true) : undefined}
      onMouseLeave={isVerse ? () => p.onHover?.(false) : undefined}
    >
      <div className="hit-head">
        <span className="hit-rank">{hit.rank}</span>
        <Link className="hit-ref" to={unitLink(hit.unit.unit_id)}>
          <UnitName en={hit.unit.label_en} he={hit.unit.label_he} />
        </Link>
        <LinkBadge link={hit.link} />
        {hit.phrase && (
          <span className="phrase-tag" title={m.hit.phraseTitle(hit.phrase.n_tokens, hit.phrase.score.toFixed(1))}>
            {m.hit.phrase(hit.phrase.n_tokens)}
          </span>
        )}
        <ScoreBreakdown hit={hit} mode={mode} />
        <span className="hit-actions">
          {isVerse && (
            <button
              type="button"
              className="linkish"
              aria-pressed={p.pinned}
              onClick={p.onTogglePin}
              title={changes ? m.hit.keepChanges : m.hit.keepShared}
            >
              {p.pinned ? m.hit.unpin : changes ? m.hit.changes : m.hit.sharedWords}
            </button>
          )}
          <Link className="linkish" to={compareLink(source.unit_id, hit.unit.unit_id)} title={m.hit.compareTitle}>
            {m.hit.compare}
          </Link>
        </span>
      </div>
      {hit.verse ? (
        <p className="hit-text">
          <HebrewText verse={hit.verse} highlight={highlight} />
        </p>
      ) : (
        hit.preview && (
          <p className="hit-text preview">
            <HebrewPlain text={hit.preview} />
            {hit.unit.n_verses > 1 && <span className="muted">{m.hit.moreVerses(hit.unit.n_verses)}</span>}
          </p>
        )
      )}
      {p.active && isVerse && changes && (
        <div className="small">
          {p.diff?.loose ? (
            <span className="muted">{m.diff.tooDifferent}</span>
          ) : (
            p.diff && <DiffLegend />
          )}
        </div>
      )}
      {p.active && isVerse && !changes && (
        <LemmaChips explain={explain} loading={p.explainLoading} focus={p.focusLemma} onFocus={p.onFocusLemma} />
      )}
    </li>
  )
}

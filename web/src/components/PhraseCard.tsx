import { Link } from 'react-router'
import type { PhrasePair, UnitSummary, Verse } from '../api/types'
import type { Highlight } from '../lib/highlight'
import { compareLink, unitLink } from '../lib/links'
import { HebrewText } from './HebrewText'
import { useT } from '../context/localeContext'
import { LinkBadge } from './LinkBadge'
import { UnitName } from './UnitName'

const marks = (idxs: number[]): Highlight => new Map(idxs.map((i) => [i, 'shared']))

/** Two verses sharing an aligned phrase, the matched words highlighted on both sides. */
export function PhraseCard({ p }: { p: PhrasePair }) {
  const m = useT()
  return (
    <li className="disc">
      <div className="hit-head">
        <span className="score" title={m.cards.phraseScore}>
          {p.score.toFixed(1)}
        </span>
        <span className="phrase-tag">{m.cards.lemmas(p.n_tokens)}</span>
        {p.spread > 2 && (
          <span className="muted small" title={m.cards.recursTitle}>
            {m.cards.recurs(p.spread)}
          </span>
        )}
        <LinkBadge link={p.link} />
        <span className="hit-actions">
          <Link className="linkish" to={compareLink(p.a.unit_id, p.b.unit_id)} title={m.hit.compareTitle}>
            {m.hit.compare}
          </Link>
        </span>
      </div>
      <div className="disc-pair">
        <Side unit={p.a} verse={p.a_verse} display={p.a_display} />
        <Side unit={p.b} verse={p.b_verse} display={p.b_display} />
      </div>
    </li>
  )
}

function Side({ unit, verse, display }: { unit: UnitSummary; verse: Verse; display: number[] }) {
  return (
    <div className="disc-side">
      <Link className="hit-ref" to={unitLink(unit.unit_id)}>
        <UnitName en={unit.label_en} he={unit.label_he} />
      </Link>
      <p className="hit-text">
        <HebrewText verse={verse} highlight={marks(display)} />
      </p>
    </div>
  )
}

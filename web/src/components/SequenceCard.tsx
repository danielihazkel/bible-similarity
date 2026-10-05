import { Link } from 'react-router'
import type { SequenceSummary } from '../api/types'
import { qLabel } from '../lib/format'
import { sequenceLink, unitLink } from '../lib/links'

const Q_TITLE =
  'Expected share of chance chains among chains at least this strong (verse order shuffled within chapters)'

/** Two passages that run parallel verse by verse; opens the side-by-side ladder. */
export function SequenceCard({ s }: { s: SequenceSummary }) {
  return (
    <li className="disc">
      <div className="hit-head">
        <span className="score" title="Chain score: pair weights minus gap costs">
          {s.score.toFixed(1)}
        </span>
        <span className="phrase-tag">
          {s.n_pairs} verses {s.direction === 'reverse' ? 'in mirrored order' : s.direction === 'mixed' ? 'reordered' : 'in order'}
        </span>
        <span className={`small ${s.q <= 0.05 ? 'q-strong' : 'muted'}`} title={Q_TITLE}>
          {qLabel(s.q)}
        </span>
        <span className="muted small" title="Aligned verse pairs that Sefaria already links">
          {s.n_gold === 0 ? 'not linked in Sefaria' : `Sefaria links ${s.n_gold}/${s.n_pairs}`}
        </span>
        <span className="hit-actions">
          <Link className="linkish" to={sequenceLink(s.seq_id)}>
            Side by side
          </Link>
        </span>
      </div>
      <div className="disc-pair">
        <Span id={s.a_start} en={s.a_label} he={s.a_label_he} />
        <Span id={s.b_start} en={s.b_label} he={s.b_label_he} />
      </div>
    </li>
  )
}

function Span({ id, en, he }: { id: number; en: string; he: string }) {
  return (
    <div className="disc-side">
      <Link className="hit-ref" to={unitLink(`v:${id}`)}>
        {en}
        <span className="he-label" dir="rtl" lang="he">
          {he}
        </span>
      </Link>
    </div>
  )
}

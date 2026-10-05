import { Link } from 'react-router'
import type { SequenceSummary } from '../api/types'
import { useT } from '../context/localeContext'
import { sequenceLink, unitLink } from '../lib/links'
import { UnitName } from './UnitName'

/** Two passages that run parallel verse by verse; opens the side-by-side ladder. */
export function SequenceCard({ s }: { s: SequenceSummary }) {
  const m = useT()
  return (
    <li className="disc">
      <div className="hit-head">
        <span className="score" title={m.cards.chainScore}>
          {s.score.toFixed(1)}
        </span>
        <span className="phrase-tag">
          {m.cards.seqVerses(s.n_pairs, s.direction)}
        </span>
        <span className={`small ${s.q <= 0.05 ? 'q-strong' : 'muted'}`} title={m.cards.qTitle}>
          {m.q(s.q)}
        </span>
        <span className="muted small" title={m.cards.goldTitle}>
          {s.n_gold === 0 ? m.cards.notLinked : m.cards.linksOf(s.n_gold, s.n_pairs)}
        </span>
        <span className="hit-actions">
          <Link className="linkish" to={sequenceLink(s.seq_id)}>
            {m.cards.sideBySide}
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
        <UnitName en={en} he={he} />
      </Link>
    </div>
  )
}

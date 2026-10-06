import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useSequence } from '../api/hooks'
import type { LadderRow, Verse } from '../api/types'
import { BorrowLineForSequence } from '../components/BorrowLine'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { similarityBand } from '../lib/format'
import { diffHighlight, type Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { verseRef } from '../lib/names'

/** One parallel sequence as a ladder: aligned verse pairs side by side, skipped verses alone on their side. */
export function SequencePage() {
  const { m, locale } = useLocale()
  const { seqId } = useParams()
  const id = Number(seqId)
  const valid = Number.isInteger(id) && id > 0
  const res = useSequence(valid ? id : undefined)
  const [showChanges, setShowChanges] = useState(true)
  if (!valid) return <p className="status">{m.par.sequence.notId}</p>
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { sequence: s, rows, verses } = res.data
  const verse = (v: number | null) => (v === null ? undefined : verses[String(v)])
  const onlyA = rows.filter((r) => r.b === null).length
  const onlyB = rows.filter((r) => r.a === null).length

  return (
    <div className="page sequence-page">
      <nav className="crumbs" aria-label={m.units.context}>
        <Link to="/sequences">{m.par.sequences.title}</Link>
      </nav>
      <h1>
        {locale === 'he' ? s.a_label_he : s.a_label} <span className="muted">↔</span>{' '}
        {locale === 'he' ? s.b_label_he : s.b_label}
      </h1>
      {locale === 'en' && (
        <p className="muted">
          <span dir="rtl" lang="he">
            {s.a_label_he}
          </span>{' '}
          ↔{' '}
          <span dir="rtl" lang="he">
            {s.b_label_he}
          </span>
        </p>
      )}
      <p className="lede">
        {m.par.sequence.versePairs(s.n_pairs)}{' '}
        {m.par.sequence.directions[s.direction ?? 'forward'] ?? m.par.sequence.directions.forward}{' '}
        · {m.q(s.q)} · {m.par.sequence.score(s.score.toFixed(1))} ·{' '}
        {s.n_gold === 0 ? m.par.sequence.noneLinked : m.par.sequence.linked(s.n_gold)}
        {onlyA + onlyB > 0 && m.par.sequence.onlySides(onlyA, onlyB)}
      </p>
      <BorrowLineForSequence seqId={s.seq_id} />
      <div className="toolbar">
        <label className="check">
          <input type="checkbox" checked={showChanges} onChange={(e) => setShowChanges(e.target.checked)} />
          {m.par.sequence.markChanges}
        </label>
        {showChanges && <DiffLegend />}
        {showChanges && <span className="muted small">{m.par.sequence.loose}</span>}
      </div>
      <ol className="ladder" aria-label={m.par.sequence.aligned}>
        {rows.map((r) => (
          <Rung key={`${r.a}|${r.b}`} row={r} a={verse(r.a)} b={verse(r.b)} marks={showChanges} />
        ))}
      </ol>
    </div>
  )
}

function Rung({ row, a, b, marks }: { row: LadderRow; a?: Verse; b?: Verse; marks: boolean }) {
  const m = useT()
  const pair = row.a !== null && row.b !== null
  return (
    <li className={`rung ${pair ? '' : 'skip'}`}>
      <Side verse={a} highlight={marks ? diffHighlight(row.a_marks) : undefined} />
      <div className="rung-mid">
        {pair && row.cosine !== null && (
          <span
            className={`sim-swatch sim-${similarityBand(row.cosine)}`}
            title={m.par.sequence.cosineTitle(row.cosine.toFixed(2), !!row.gold, !!row.loose)}
          >
            {row.gold ? '★' : row.loose ? '≈' : ''}
          </span>
        )}
        {pair && row.cosine !== null && <span className="rung-cos">{row.cosine.toFixed(2)}</span>}
      </div>
      <Side verse={b} highlight={marks ? diffHighlight(row.b_marks) : undefined} />
    </li>
  )
}

function Side({ verse, highlight }: { verse?: Verse; highlight?: Highlight }) {
  const { locale } = useLocale()
  if (!verse) return <div className="rung-side empty" />
  return (
    <div className="rung-side">
      <Link className="hit-ref" to={unitLink(`v:${verse.verse_id}`)}>
        {verseRef(verse, locale)}
      </Link>
      <p className="hit-text">
        <HebrewText verse={verse} highlight={highlight} />
      </p>
    </div>
  )
}

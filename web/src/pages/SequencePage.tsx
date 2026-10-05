import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useSequence } from '../api/hooks'
import type { LadderRow, Verse } from '../api/types'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { qLabel, similarityBand } from '../lib/format'
import { diffHighlight, type Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'

/** One parallel sequence as a ladder: aligned verse pairs side by side, skipped verses alone on their side. */
export function SequencePage() {
  const { seqId } = useParams()
  const id = Number(seqId)
  const valid = Number.isInteger(id) && id > 0
  const res = useSequence(valid ? id : undefined)
  const [showChanges, setShowChanges] = useState(true)
  if (!valid) return <p className="status">Not a sequence id.</p>
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { sequence: s, rows, verses } = res.data
  const verse = (v: number | null) => (v === null ? undefined : verses[String(v)])
  const onlyA = rows.filter((r) => r.b === null).length
  const onlyB = rows.filter((r) => r.a === null).length

  return (
    <div className="page sequence-page">
      <nav className="crumbs" aria-label="Context">
        <Link to="/sequences">Parallel sequences</Link>
      </nav>
      <h1>
        {s.a_label} <span className="muted">↔</span> {s.b_label}
      </h1>
      <p className="muted">
        <span dir="rtl" lang="he">
          {s.a_label_he}
        </span>{' '}
        ↔{' '}
        <span dir="rtl" lang="he">
          {s.b_label_he}
        </span>
      </p>
      <p className="lede">
        {s.n_pairs} verse pairs{' '}
        {s.direction === 'reverse'
          ? 'in mirrored order (the right side runs backwards)'
          : s.direction === 'mixed'
            ? 'in another order (the right side jumps back and forth)'
            : 'in the same order'}{' '}
        · {qLabel(s.q)} · score {s.score.toFixed(1)} ·{' '}
        {s.n_gold === 0 ? 'none linked in Sefaria' : `${s.n_gold} linked in Sefaria (★)`}
        {onlyA + onlyB > 0 && ` · ${onlyA} verse(s) only on the left, ${onlyB} only on the right`}
      </p>
      <div className="toolbar">
        <label className="check">
          <input type="checkbox" checked={showChanges} onChange={(e) => setShowChanges(e.target.checked)} />
          Mark word changes
        </label>
        {showChanges && <DiffLegend />}
        {showChanges && <span className="muted small">≈ loosely parallel, not marked</span>}
      </div>
      <ol className="ladder" aria-label="Aligned verses">
        {rows.map((r) => (
          <Rung key={`${r.a}|${r.b}`} row={r} a={verse(r.a)} b={verse(r.b)} marks={showChanges} />
        ))}
      </ol>
    </div>
  )
}

function Rung({ row, a, b, marks }: { row: LadderRow; a?: Verse; b?: Verse; marks: boolean }) {
  const pair = row.a !== null && row.b !== null
  return (
    <li className={`rung ${pair ? '' : 'skip'}`}>
      <Side verse={a} highlight={marks ? diffHighlight(row.a_marks) : undefined} />
      <div className="rung-mid">
        {pair && row.cosine !== null && (
          <span
            className={`sim-swatch sim-${similarityBand(row.cosine)}`}
            title={`Cosine ${row.cosine.toFixed(2)}${row.gold ? ' · linked in Sefaria' : ''}${
              row.loose ? ' · loosely parallel: too different to mark word by word' : ''
            }`}
          >
            {row.gold ? '★' : row.loose ? '≈' : ''}
          </span>
        )}
      </div>
      <Side verse={b} highlight={marks ? diffHighlight(row.b_marks) : undefined} />
    </li>
  )
}

function Side({ verse, highlight }: { verse?: Verse; highlight?: Highlight }) {
  if (!verse) return <div className="rung-side empty" />
  return (
    <div className="rung-side">
      <Link className="hit-ref" to={unitLink(`v:${verse.verse_id}`)}>
        {verse.ref}
      </Link>
      <p className="hit-text">
        <HebrewText verse={verse} highlight={highlight} />
      </p>
    </div>
  )
}

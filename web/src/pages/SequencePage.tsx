import { Link, useParams } from 'react-router'
import { useSequence } from '../api/hooks'
import type { LadderRow, Verse } from '../api/types'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { qLabel, similarityBand } from '../lib/format'
import { unitLink } from '../lib/links'

/** One parallel sequence as a ladder: aligned verse pairs side by side, skipped verses alone on their side. */
export function SequencePage() {
  const { seqId } = useParams()
  const id = Number(seqId)
  const valid = Number.isInteger(id) && id > 0
  const res = useSequence(valid ? id : undefined)
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
        {s.n_pairs} verse pairs in the same order · {qLabel(s.q)} · score {s.score.toFixed(1)} ·{' '}
        {s.n_gold === 0 ? 'none linked in Sefaria' : `${s.n_gold} linked in Sefaria (★)`}
        {onlyA + onlyB > 0 && ` · ${onlyA} verse(s) only on the left, ${onlyB} only on the right`}
      </p>
      <ol className="ladder" aria-label="Aligned verses">
        {rows.map((r) => (
          <Rung key={`${r.a}|${r.b}`} row={r} a={verse(r.a)} b={verse(r.b)} />
        ))}
      </ol>
    </div>
  )
}

function Rung({ row, a, b }: { row: LadderRow; a?: Verse; b?: Verse }) {
  const pair = row.a !== null && row.b !== null
  return (
    <li className={`rung ${pair ? '' : 'skip'}`}>
      <Side verse={a} />
      <div className="rung-mid">
        {pair && row.cosine !== null && (
          <span
            className={`sim-swatch sim-${similarityBand(row.cosine)}`}
            title={`Cosine ${row.cosine.toFixed(2)}${row.gold ? ' · linked in Sefaria' : ''}`}
          >
            {row.gold ? '★' : ''}
          </span>
        )}
      </div>
      <Side verse={b} />
    </li>
  )
}

function Side({ verse }: { verse?: Verse }) {
  if (!verse) return <div className="rung-side empty" />
  return (
    <div className="rung-side">
      <Link className="hit-ref" to={unitLink(`v:${verse.verse_id}`)}>
        {verse.ref}
      </Link>
      <p className="hit-text">
        <HebrewText verse={verse} />
      </p>
    </div>
  )
}

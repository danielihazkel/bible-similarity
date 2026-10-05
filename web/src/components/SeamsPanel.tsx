import { Link } from 'react-router'
import { useSeams } from '../api/hooks'
import type { CurvePoint, Seam } from '../api/types'
import { useLocale, useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { ErrorBox, Loading } from './Status'

/** Where the style of a book changes: the shift curve along the book, its threshold and seams.
 * Without a book: the strongest seams of the corpus. */
export function SeamsPanel({ book, name }: { book?: number; name: Map<number, string> }) {
  const m = useT()
  const res = useSeams(book)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { curve, seams, threshold, block_words } = res.data
  return (
    <section aria-label={m.ov.seams.label}>
      <h2>{m.ov.seams.title}</h2>
      <p className="muted small">{m.ov.seams.lede(block_words)}</p>
      {book !== undefined && curve.length > 0 && threshold !== null && (
        <ShiftChart curve={curve} seams={seams} threshold={threshold} />
      )}
      {seams.length === 0 ? (
        <p className="status">{m.ov.seams.none(book !== undefined)}</p>
      ) : (
        <ol className="seam-list">
          {seams.map((s) => (
            <SeamRow key={`${s.book_id}-${s.rank}`} s={s} book={book === undefined ? name.get(s.book_id) : undefined} />
          ))}
        </ol>
      )}
    </section>
  )
}

function SeamRow({ s, book }: { s: Seam; book?: string }) {
  const { m, locale } = useLocale()
  return (
    <li>
      <Link to={unitLink(`v:${s.verse_id}`)}>{locale === 'he' ? s.label_he : s.label}</Link>
      {book && <span className="muted small"> · {book}</span>}{' '}
      <span className="muted small">
        {m.ov.seams.shift(s.shift.toFixed(2), s.threshold.toFixed(2))}
      </span>
      <span className="seam-features">
        {s.features.map((f) => (
          <span key={f.feature} className={`seam-feature ${f.z > 0 ? 'up' : 'down'}`} title={f.feature}>
            <span dir="rtl" lang="he">
              {f.label}
            </span>{' '}
            {f.z > 0 ? '↑' : '↓'}
          </span>
        ))}
      </span>
    </li>
  )
}

function ShiftChart({ curve, seams, threshold }: { curve: CurvePoint[]; seams: Seam[]; threshold: number }) {
  const { m, locale } = useLocale()
  const at = new Map(curve.map((c) => [c.verse_id, c]))
  /** chapter:verse of a seam, from the curve (labels differ per language) */
  const cv = (s: Seam) => {
    const c = at.get(s.verse_id)
    return c ? m.cv(c.chapter, c.verse) : ''
  }
  const W = 760
  const H = 180
  const pad = { l: 34, r: 8, t: 10, b: 24 }
  const lo = curve[0].verse_id
  const hi = curve[curve.length - 1].verse_id
  const ymax = Math.max(threshold, ...curve.map((c) => c.shift)) * 1.08
  const x = (v: number) => pad.l + ((v - lo) / Math.max(1, hi - lo)) * (W - pad.l - pad.r)
  const y = (s: number) => pad.t + (1 - s / ymax) * (H - pad.t - pad.b)
  // the curve is undefined near the ends and wherever a gap left too few words: break the line there
  const path = curve
    .map((c, i) => `${i > 0 && c.verse_id - curve[i - 1].verse_id > 1 ? 'M' : i === 0 ? 'M' : 'L'}${x(c.verse_id).toFixed(1)},${y(c.shift).toFixed(1)}`)
    .join(' ')
  const chapterStarts = curve.filter((c, i) => i === 0 || c.chapter !== curve[i - 1].chapter)
  const every = Math.max(1, Math.ceil(chapterStarts.length / 12))
  return (
    <svg className="shift-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={m.ov.seams.chart} direction="ltr">
      {chapterStarts.map((c, i) =>
        i % every === 0 ? (
          <g key={c.verse_id}>
            <line x1={x(c.verse_id)} x2={x(c.verse_id)} y1={pad.t} y2={H - pad.b} className="chart-grid" />
            <text x={x(c.verse_id)} y={H - 8} textAnchor="middle" className="axis">
              {c.chapter}
            </text>
          </g>
        ) : null,
      )}
      <line x1={pad.l} x2={W - pad.r} y1={y(threshold)} y2={y(threshold)} className="chart-threshold" />
      <path d={path} className="chart-line" />
      {seams.map((s) => (
        <g key={s.rank}>
          <circle cx={x(s.verse_id)} cy={y(s.shift)} r={4} className="chart-peak">
            <title>{`${locale === 'he' ? s.label_he : s.label}: ${s.shift.toFixed(2)}`}</title>
          </circle>
          {s.rank <= 5 && (
            <text x={x(s.verse_id)} y={y(s.shift) - 7} textAnchor="middle" className="axis">
              {cv(s)}
            </text>
          )}
        </g>
      ))}
      <text x={4} y={y(threshold) - 3} className="axis">
        {threshold.toFixed(2)}
      </text>
    </svg>
  )
}

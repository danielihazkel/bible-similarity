import { useMemo } from 'react'
import { Link } from 'react-router'
import { useSequenceArcs } from '../api/hooks'
import type { Book, SequenceDirection, SequenceSummary } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import { bookName } from '../lib/names'

const W = 1000
const H = 380
const PAD = 12
const BASE = H - 46 // the line the books sit on
const BAND = 12
const SECTIONS = ['Torah', 'Prophets', 'Writings']
const SECTION_HUES = [210, 25, 140]

interface Props {
  maxQ?: number
  direction?: SequenceDirection
  book?: number
  crossBook: boolean
  hideSameChapter: boolean
  books: Book[]
}

/** Every parallel sequence as an arc over the books in canon order (Hebrew: right to left). */
export function SequenceArcs({ maxQ, direction, book, crossBook, hideSameChapter, books }: Props) {
  const { m, locale } = useLocale()
  const t = m.par.sequences.arcs
  const res = useSequenceArcs({ maxQ, direction })
  const byId = useMemo(() => new Map(books.map((b) => [b.book_id, b])), [books])
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { items, total, books: spans } = res.data
  const shown = items.filter((s) => (!crossBook || s.a_book !== s.b_book) && (!hideSameChapter || !s.same_chapter))
  const nVerses = spans.length ? spans[spans.length - 1].end + 1 : 1
  const rtl = locale === 'he'
  const x = (v: number) => {
    const f = v / nVerses
    return PAD + (rtl ? 1 - f : f) * (W - 2 * PAD)
  }
  // the widest possible arc spans the whole line; scale heights so it still fits
  const k = (BASE - 16) / ((W - 2 * PAD) / 2)
  const maxPairs = Math.max(1, ...shown.map((s) => s.n_pairs))
  const touches = (s: SequenceSummary) => book === undefined || s.a_book === book || s.b_book === book
  // thin arcs first, so the strong ones are drawn on top
  const ordered = [...shown].sort((a, b) => Number(touches(a)) - Number(touches(b)) || a.n_pairs - b.n_pairs)
  const cross = shown.filter((s) => s.a_book !== s.b_book).length
  const label = (s: SequenceSummary) =>
    t.arc(locale === 'he' ? s.a_label_he : s.a_label, locale === 'he' ? s.b_label_he : s.b_label, s.n_pairs)

  return (
    <section aria-label={t.label} className="arcs">
      <p className="muted small">
        {t.count(shown.length, cross)}
        {items.length < total && t.capped(items.length, total)}
      </p>
      <p className="muted small">{t.legend}</p>
      <p className="section-legend small" aria-hidden="true">
        <span>
          <span className="swatch arc-cross" /> {t.crossBook}
        </span>
        <span>
          <span className="swatch arc-within" /> {t.withinBook}
        </span>
      </p>
      <svg className="arc-diagram" viewBox={`0 0 ${W} ${H}`} role="group" aria-label={t.label} direction="ltr">
        {ordered.map((s) => {
          const xa = x((s.a_start + s.a_end) / 2)
          const xb = x((s.b_start + s.b_end) / 2)
          const [x0, x1] = xa < xb ? [xa, xb] : [xb, xa]
          const r = Math.max((x1 - x0) / 2, 0.5)
          const on = touches(s)
          return (
            // a router Link inside <svg> renders an SVG <a>, keeping client-side navigation
            <Link key={s.seq_id} to={`/sequences/${s.seq_id}`} aria-label={label(s)} className={on ? 'arc' : 'arc faded'}>
              <title>{label(s)}</title>
              <path
                d={`M ${x0} ${BASE} A ${r} ${r * k} 0 0 1 ${x1} ${BASE}`}
                className={s.a_book !== s.b_book ? 'arc-cross' : 'arc-within'}
                strokeWidth={0.6 + 2.6 * Math.sqrt(s.n_pairs / maxPairs)}
              />
            </Link>
          )
        })}
        <g className="arc-books">
          {spans.map((b, i) => {
            const info = byId.get(b.book_id)
            const name = info ? bookName(info, locale) : String(b.book_id)
            const xs = [x(b.start), x(b.end + 1)]
            const left = Math.min(...xs)
            const width = Math.abs(xs[1] - xs[0])
            const hue = SECTION_HUES[Math.max(0, SECTIONS.indexOf(info?.section ?? 'Torah'))]
            const short = locale === 'he' ? (info?.he_name ?? name) : (info?.osis ?? name)
            return (
              <g key={b.book_id} className={book === b.book_id ? 'arc-book on' : 'arc-book'}>
                <rect x={left} y={BASE} width={width} height={BAND} fill={`hsl(${hue}, 55%, ${i % 2 ? 62 : 48}%)`}>
                  <title>{name}</title>
                </rect>
                {width >= short.length * 6.5 && (
                  <text x={left + width / 2} y={BASE + BAND + 13} textAnchor="middle" className="arc-book-label">
                    {short}
                  </text>
                )}
              </g>
            )
          })}
        </g>
      </svg>
    </section>
  )
}

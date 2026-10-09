import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useBookStyle, useStylometry } from '../api/hooks'
import type { Book, StyloPoint } from '../api/types'
import { FeatureBars as Features } from '../components/FeatureBars'
import { BookHeatmap } from '../components/BookHeatmap'
import { SeamsPanel } from '../components/SeamsPanel'
import { Scatter } from '../components/Scatter'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { bookName, bookOption, unitLabel } from '../lib/names'
import { useQueryParams } from '../lib/urlState'

const SECTIONS = ['Torah', 'Prophets', 'Writings']
const HUES = [210, 25, 140]
const color = (i: number, alpha: number) => `hsla(${HUES[i] ?? 0}, 62%, 46%, ${alpha})`

/** Style profiles: chapter PCA of function-word and morphology rates, books by Burrows' Delta. */
export function StylometryPage() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const books = useBooks()
  const st = useStylometry()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const [pair, setPair] = useState<string | null>(null)

  if (st.isPending || books.isPending) return <Loading />
  if (st.error) return <ErrorBox error={st.error} />
  if (books.error) return <ErrorBox error={books.error} />
  const name = new Map(books.data.map((b) => [b.book_id, bookName(b, locale)]))
  const deltas = new Map<string, number>()
  for (const d of st.data.delta) {
    deltas.set(`${d.a}-${d.b}`, d.delta)
    deltas.set(`${d.b}-${d.a}`, d.delta)
  }
  const values = st.data.delta.map((d) => d.delta)
  const lo = Math.min(...values)
  const hi = Math.max(...values)

  return (
    <div className="page stylometry-page">
      <h1>{m.ov.style.title}</h1>
      <p className="lede">{m.ov.style.lede}</p>
      <div className="toolbar">
        <label className="control">
          <span>{m.ov.style.book}</span>
          <select value={book ?? ''} onChange={(e) => update({ book: e.target.value || null })}>
            <option value="">{m.ov.style.highlight}</option>
            {books.data.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="map-grid">
        <StyleScatter points={st.data.points} books={books.data} book={book} />
        <div className="axes-notes">
          {st.data.axes.map((a) => (
            <p key={a.pc} className="fact">
              <strong>{m.ov.style.axis(a.pc)}</strong>{' '}
              <span className="muted small">{m.ov.style.variance(a.variance)}</span>
              <br />
              <span className="muted small">{m.ov.style.positive(a.pc)}:</span>{' '}
              <span dir="rtl" lang="he" className="he">
                {a.positive.join(' · ')}
              </span>
              <br />
              <span className="muted small">{m.ov.style.negative(a.pc)}:</span>{' '}
              <span dir="rtl" lang="he" className="he">
                {a.negative.join(' · ')}
              </span>
            </p>
          ))}
          <ul className="cluster-legend">
            {SECTIONS.map((s, i) => (
              <li key={s}>
                <span className="legend-row">
                  <span className="swatch" style={{ background: color(i, 1) }} /> {m.units.sections[s] ?? s}
                </span>
              </li>
            ))}
          </ul>
          {book !== undefined && <BookProfile book={book} name={name} />}
        </div>
      </div>

      <SeamsPanel book={book} name={name} />

      <h2>{m.ov.style.distance}</h2>
      <p className="muted small">{m.ov.style.distanceLede}</p>
      <BookHeatmap
        books={books.data}
        order={st.data.order.length ? st.data.order : books.data.map((b) => b.book_id)}
        value={(a, b) => {
          const d = deltas.get(`${a}-${b}`)
          return d === undefined || hi === lo ? undefined : 1 - (d - lo) / (hi - lo)
        }}
        title={(a, b) => m.ov.style.delta(String(name.get(a)), String(name.get(b)), (deltas.get(`${a}-${b}`) ?? 0).toFixed(2))}
        selected={pair}
        onSelect={(k) => {
          setPair(k)
          if (k) update({ book: k.split('-')[0] })
        }}
        label={m.ov.style.distance}
      />
    </div>
  )
}

function BookProfile({ book, name }: { book: number; name: Map<number, string> }) {
  const m = useT()
  const res = useBookStyle(book)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const p = res.data
  return (
    <section className="book-profile" aria-label={m.ov.style.profile}>
      <h3>
        {name.get(book)} <span className="muted small">{m.ov.style.words(p.n_words)}</span>
      </h3>
      <Features title={m.ov.style.more} items={p.over} />
      <Features title={m.ov.style.less} items={p.under} />
      <p className="small">
        <span className="muted">{m.ov.style.closest}</span> {p.closest.map((c) => `${name.get(c.b)} (${c.delta.toFixed(2)})`).join(', ')}
      </p>
    </section>
  )
}

function StyleScatter({ points, books, book }: { points: StyloPoint[]; books: Book[]; book?: number }) {
  const { m, locale } = useLocale()
  const section = useMemo(() => new Map(books.map((b) => [b.book_id, SECTIONS.indexOf(b.section)])), [books])
  const on = (p: StyloPoint) => book !== undefined && p.book_id === book
  return (
    <Scatter
      points={points}
      width={720}
      height={520}
      label={m.ov.style.scatter}
      fill={(p) => color(section.get(p.book_id) ?? 0, book === undefined ? 0.75 : on(p) ? 0.95 : 0.1)}
      radius={(p) => (on(p) ? 5.5 : 4)}
      front={book === undefined ? undefined : on}
      caption={(p) => (
        <>
          <Link to={unitLink(p.unit_id)}>{unitLabel(p, locale)}</Link>
          {m.ov.style.point(p.n_words)}
        </>
      )}
      idle={m.ov.style.idle}
    />
  )
}

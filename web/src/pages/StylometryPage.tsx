import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useBookStyle, useStylometry } from '../api/hooks'
import type { Book, StyloFeature, StyloPoint } from '../api/types'
import { BookHeatmap } from '../components/BookHeatmap'
import { Scatter } from '../components/Scatter'
import { ErrorBox, Loading } from '../components/Status'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

const SECTIONS = ['Torah', 'Prophets', 'Writings']
const HUES = [210, 25, 140]
const color = (i: number, alpha: number) => `hsla(${HUES[i] ?? 0}, 62%, 46%, ${alpha})`

/** Style profiles: chapter PCA of function-word and morphology rates, books by Burrows' Delta. */
export function StylometryPage() {
  const [params, update] = useQueryParams()
  const books = useBooks()
  const st = useStylometry()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const [pair, setPair] = useState<string | null>(null)

  if (st.isPending || books.isPending) return <Loading />
  if (st.error) return <ErrorBox error={st.error} />
  if (books.error) return <ErrorBox error={books.error} />
  const name = new Map(books.data.map((b) => [b.book_id, b.name]))
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
      <h1>Style</h1>
      <p className="lede">
        How the books write, not what they say: rates of the 100 most frequent lemmas and of grammatical forms (wayyiqtol,
        participles, the article, suffixes …), compared across books and chapters. These are descriptive statistics;
        groupings are not claims about authorship or date.
      </p>
      <div className="toolbar">
        <label className="control">
          <span>Book</span>
          <select value={book ?? ''} onChange={(e) => update({ book: e.target.value || null })}>
            <option value="">— highlight a book —</option>
            {books.data.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {b.name} · {b.he_name}
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
              <strong>{a.pc === 1 ? 'Horizontal' : 'Vertical'} axis</strong>{' '}
              <span className="muted small">({Math.round(a.variance * 100)} % of the variance)</span>
              <br />
              <span className="muted small">{a.pc === 1 ? 'right' : 'up'}:</span>{' '}
              <span dir="rtl" lang="he" className="he">
                {a.positive.join(' · ')}
              </span>
              <br />
              <span className="muted small">{a.pc === 1 ? 'left' : 'down'}:</span>{' '}
              <span dir="rtl" lang="he" className="he">
                {a.negative.join(' · ')}
              </span>
            </p>
          ))}
          <ul className="cluster-legend">
            {SECTIONS.map((s, i) => (
              <li key={s}>
                <span className="legend-row">
                  <span className="swatch" style={{ background: color(i, 1) }} /> {s}
                </span>
              </li>
            ))}
          </ul>
          {book !== undefined && <BookProfile book={book} name={name} />}
        </div>
      </div>

      <h2>Stylistic distance between books</h2>
      <p className="muted small">
        Burrows' Delta (mean difference of feature z-scores); darker = more alike. Books are ordered so similar styles sit
        together.
      </p>
      <BookHeatmap
        books={books.data}
        order={st.data.order.length ? st.data.order : books.data.map((b) => b.book_id)}
        value={(a, b) => {
          const d = deltas.get(`${a}-${b}`)
          return d === undefined || hi === lo ? undefined : 1 - (d - lo) / (hi - lo)
        }}
        title={(a, b) => `${name.get(a)} ↔ ${name.get(b)}: Delta ${(deltas.get(`${a}-${b}`) ?? 0).toFixed(2)}`}
        selected={pair}
        onSelect={(k) => {
          setPair(k)
          if (k) update({ book: k.split('-')[0] })
        }}
        label="Stylistic distance between books"
      />
    </div>
  )
}

function BookProfile({ book, name }: { book: number; name: Map<number, string> }) {
  const res = useBookStyle(book)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const p = res.data
  return (
    <section className="book-profile" aria-label="Book style profile">
      <h3>
        {name.get(book)} <span className="muted small">({p.n_words.toLocaleString()} words)</span>
      </h3>
      <Features title="Uses more than other books" items={p.over} />
      <Features title="Uses less" items={p.under} />
      <p className="small">
        <span className="muted">Closest in style:</span> {p.closest.map((c) => `${name.get(c.b)} (${c.delta.toFixed(2)})`).join(', ')}
      </p>
    </section>
  )
}

function Features({ title, items }: { title: string; items: StyloFeature[] }) {
  const max = Math.max(...items.map((f) => Math.abs(f.z)), 1)
  return (
    <>
      <p className="muted small">{title}</p>
      <ul className="feature-bars">
        {items.map((f) => (
          <li key={f.feature} title={`${f.feature}: ${(f.rate * 100).toFixed(2)} per 100 words, z ${f.z.toFixed(1)}`}>
            <span dir="rtl" lang="he" className="he">
              {f.label}
            </span>
            <span className="bar-track">
              <span className={`bar-fill ${f.z < 0 ? 'neg' : ''}`} style={{ width: `${(Math.abs(f.z) / max) * 100}%` }} />
            </span>
            <span className="bar-n">{f.z > 0 ? '+' : ''}{f.z.toFixed(1)}</span>
          </li>
        ))}
      </ul>
    </>
  )
}

function StyleScatter({ points, books, book }: { points: StyloPoint[]; books: Book[]; book?: number }) {
  const section = useMemo(() => new Map(books.map((b) => [b.book_id, SECTIONS.indexOf(b.section)])), [books])
  const on = (p: StyloPoint) => book !== undefined && p.book_id === book
  return (
    <Scatter
      points={points}
      width={720}
      height={520}
      label="Chapters by style"
      fill={(p) => color(section.get(p.book_id) ?? 0, book === undefined ? 0.75 : on(p) ? 0.95 : 0.1)}
      radius={(p) => (on(p) ? 5.5 : 4)}
      front={book === undefined ? undefined : on}
      caption={(p) => (
        <>
          <Link to={unitLink(p.unit_id)}>{p.label_en}</Link> · {p.n_words} words
        </>
      )}
      idle="Each point is a chapter (≥ 150 words). Hover for its name; click to open it."
    />
  )
}

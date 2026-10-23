import { Link, useNavigate } from 'react-router'
import { useBooks, useDivine, useDivinePairs } from '../api/hooks'
import type { Book, DivineBook, DivineChapter, DivineName, DivineResponse } from '../api/types'
import { useLocale } from '../context/localeContext'
import { readLink, unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { shareStep } from '../lib/divine'
import { useQueryParams } from '../lib/urlState'
import { formatP } from '../lib/workbench'

const PER_ROW = 50 // chapters in one row of a book's strip
const CELL = 10
const STEP = 12 // a cell and the 2px surface gap after it

const other = (c: { counts: Record<string, number> }, measure: string[]) =>
  Object.entries(c.counts).reduce((s, [k, v]) => (measure.includes(k) ? s : s + v), 0)

/** The divine names across the canon (§16.65): each chapter's mix of יהוה and אלהים, the books
 * whose mix changes, the Elohistic Psalter and the doubled psalms. */
export function DivinePage() {
  const { m } = useLocale()
  const t = m.dv
  const res = useDivine()
  const d = res.data
  return (
    <div className="page divine-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Strip d={d} />
          <Books d={d} />
          <Pairs />
          <p className="muted small">{t.method}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.dv
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: DivineResponse }) {
  const t = useLocale().m.dv
  const e = d.elohistic
  const c = d.doubled
  return (
    <section aria-labelledby="dv-checks">
      <h2 id="dv-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.elohistic.title} <Verdict holds={e.holds} />
          </h3>
          {e.first !== null && e.last !== null && e.shares && e.p !== null ? (
            <p>{t.elohistic.text(e.first, e.last, [e.named[0], e.named[1]], e.shares, e.p)}</p>
          ) : (
            <p className="muted">{t.elohistic.notSplit}</p>
          )}
        </article>
        <article className="dv-check">
          <h3>
            {t.doubled.title} <Verdict holds={c.holds} />
          </h3>
          <p>
            {t.doubled.text(c.e_ward, c.y_ward, c.p, c.pairs.length)} <a href="#pairs">{t.pairsTitle}</a>
          </p>
          {c.missing.length > 0 && <p className="muted small">{t.doubled.missing(c.missing.join(', '))}</p>}
        </article>
      </div>
    </section>
  )
}

function Legend() {
  const t = useLocale().m.dv
  const steps: [string, string][] = [
    ['e2', t.legend.allE],
    ['e1', ''],
    ['mid', t.legend.even],
    ['y1', ''],
    ['y2', t.legend.allY],
  ]
  return (
    <div className="dv-legend" role="group" aria-label={t.legend.label}>
      <span className="dv-ramp">
        {steps.map(([s, label]) => (
          <span key={s} className="dv-ramp-step">
            <span className={`dv-swatch dv-${s}`} aria-hidden="true" />
            {label && <span className="small">{label}</span>}
          </span>
        ))}
      </span>
      <span className="dv-ramp-step">
        <span className="dv-swatch dv-none" aria-hidden="true" />
        <span className="small">{t.legend.none}</span>
      </span>
    </div>
  )
}

function Strip({ d }: { d: DivineResponse }) {
  const { m, locale } = useLocale()
  const t = m.dv
  const books = useBooks()
  const byId = new Map((books.data ?? []).map((b) => [b.book_id, b]))
  const chapters = new Map<number, DivineChapter[]>()
  for (const c of d.chapters) chapters.set(c.book_id, [...(chapters.get(c.book_id) ?? []), c])
  return (
    <section aria-labelledby="dv-strip">
      <h2 id="dv-strip">{t.stripTitle}</h2>
      <p className="muted small">{t.stripHint}</p>
      <Legend />
      <div className="dv-strip">
        {d.books.map((b) => {
          const book = byId.get(b.book_id)
          const name = book ? bookName(book, locale) : String(b.book_id)
          return (
            <div key={b.book_id} className="dv-row">
              <Link className="dv-book" to={`/divine?book=${b.book_id}#chapters`}>
                {name}
              </Link>
              <BookStrip name={name} book={b} chapters={chapters.get(b.book_id) ?? []} measure={d.measure} alpha={d.alpha} />
            </div>
          )
        })}
      </div>
    </section>
  )
}

function BookStrip({ name, book, chapters, measure, alpha }: { name: string; book: DivineBook; chapters: DivineChapter[]; measure: string[]; alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.dv
  const navigate = useNavigate()
  const rows = Math.ceil(chapters.length / PER_ROW)
  const width = Math.min(chapters.length, PER_ROW) * STEP
  const cut = book.split && book.q !== null && book.q <= alpha ? new Set([book.cut1, book.cut2]) : new Set<number | null>()
  return (
    <svg className="dv-cells" viewBox={`0 0 ${width} ${rows * STEP}`} width={width} role="img" aria-label={t.stripLabel(name)}>
      {chapters.map((c, i) => {
        const x = (i % PER_ROW) * STEP
        const y = Math.floor(i / PER_ROW) * STEP
        const label = `${name} ${c.chapter.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US')}`
        return (
          <g key={c.unit_id}>
            <rect
              className={`dv-cell dv-${shareStep(c.share)}`}
              x={x}
              y={y}
              width={CELL}
              height={CELL}
              rx={2}
              onClick={() => navigate(readLink(c.unit_id, '?layers=divine'))}
            >
              <title>{t.chapterTitle(label, c.counts[measure[0]] ?? 0, c.counts[measure[1]] ?? 0, other(c, measure))}</title>
            </rect>
            {cut.has(c.chapter) && <rect className="dv-cut" x={x - 2} y={y - 1} width={2} height={CELL + 2} />}
          </g>
        )
      })}
    </svg>
  )
}

function Books({ d }: { d: DivineResponse }) {
  const { m, locale } = useLocale()
  const t = m.dv
  const books = useBooks()
  const [params, update] = useQueryParams()
  const bp = params.get('book')
  const selected = bp === null || bp === '' ? undefined : Number(bp)
  const byId = new Map((books.data ?? []).map((b) => [b.book_id, b]))
  const nm = (id: number) => {
    const b = byId.get(id)
    return b ? bookName(b, locale) : String(id)
  }
  const num = (x: number) => x.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US')
  const pctOf = (x: number | null) => (x === null ? '—' : `${Math.round(x * 100)}%`)
  return (
    <section>
      <h2>{t.booksTitle}</h2>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
        <table className="change-table dv-table">
          <thead>
            <tr>
              <th>{t.cols.book}</th>
              <th className="num">{t.cols.chapters}</th>
              <th className="num">{t.cols.yhwh}</th>
              <th className="num">{t.cols.elohim}</th>
              <th className="num">{t.cols.other}</th>
              <th className="num">{t.cols.share}</th>
              <th className="num">{t.cols.split}</th>
              <th className="num">{t.cols.shares}</th>
              <th className="num">{t.cols.p}</th>
              <th className="num">{t.cols.q}</th>
            </tr>
          </thead>
          <tbody>
            {d.books.map((b) => (
              <tr key={b.book_id} className={b.split && b.q !== null && b.q <= d.alpha ? 'dv-sig' : undefined}>
                <td>
                  <button type="button" className="linkish" aria-pressed={b.book_id === selected} onClick={() => update({ book: b.book_id === selected ? null : String(b.book_id) })} title={t.showBook(nm(b.book_id))}>
                    {nm(b.book_id)}
                  </button>
                </td>
                <td className="num">{num(b.chapters)}</td>
                <td className="num">{num(b.counts[d.measure[0]] ?? 0)}</td>
                <td className="num">{num(b.counts[d.measure[1]] ?? 0)}</td>
                <td className="num">{num(other(b, d.measure))}</td>
                <td className="num">{pctOf(b.share)}</td>
                <td className="num">{b.split && b.cut1 !== null && b.cut2 !== null ? t.split(b.cut1, b.cut2) : t.notSplit}</td>
                <td className="num">{b.split ? b.shares.map(pctOf).join(' · ') : t.notSplit}</td>
                <td className="num">{b.p === null ? t.notSplit : formatP(b.p)}</td>
                <td className="num">{b.q === null ? t.notSplit : formatP(b.q)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected !== undefined && <BookChapters book={byId.get(selected)} bookId={selected} d={d} />}
    </section>
  )
}

function BookChapters({ book, bookId, d }: { book: Book | undefined; bookId: number; d: DivineResponse }) {
  const { m, locale } = useLocale()
  const t = m.dv
  const name = book ? bookName(book, locale) : String(bookId)
  const rows = d.chapters.filter((c) => c.book_id === bookId)
  const num = (x: number) => x.toLocaleString(locale === 'he' ? 'he-IL' : 'en-US')
  return (
    <div className="table-wrap" id="chapters" tabIndex={0} role="region" aria-label={t.chaptersTitle(name)}>
      <table className="change-table dv-table">
        <caption>{t.chaptersTitle(name)}</caption>
        <thead>
          <tr>
            <th>{t.cols.chapter}</th>
            <th className="num">{t.cols.words}</th>
            <th>{t.cols.names}</th>
            <th className="num">{t.cols.share}</th>
            <th className="num">{t.cols.part}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.unit_id}>
              <td>
                <span className={`dv-swatch dv-${shareStep(c.share)}`} aria-hidden="true" />{' '}
                <Link to={readLink(c.unit_id, '?layers=divine')}>{num(c.chapter)}</Link>
              </td>
              <td className="num">{num(c.words)}</td>
              <td>
                {Object.entries(c.counts).map(([k, v]) => (
                  <span key={k} className="dv-count">
                    <span dir="rtl" lang="he">
                      {t.names[k as DivineName]}
                    </span>{' '}
                    {num(v)}
                  </span>
                ))}
              </td>
              <td className="num">{c.share === null ? '—' : `${Math.round(c.share * 100)}%`}</td>
              <td className="num">{c.part ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Pairs() {
  const { m, locale } = useLocale()
  const t = m.dv
  const res = useDivinePairs()
  const label = (en: string | null, he: string | null) => (locale === 'he' ? he : en) ?? t.absent
  return (
    <section id="pairs" aria-labelledby="dv-pairs">
      <h2 id="dv-pairs">{t.pairsTitle}</h2>
      {(res.data?.pairs ?? []).map((p) => (
        <div key={p.pair} className="dv-pair">
          <h3>{t.pairHead(p.e, p.y)}</h3>
          <p className="muted small">{t.pairCounts(p.e_ward, p.y_ward, p.same)}</p>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={t.pairHead(p.e, p.y)}>
            <table className="change-table dv-table">
              <thead>
                <tr>
                  <th>{t.placeCols.inside}</th>
                  <th>{t.placeCols.outside}</th>
                  <th>{t.placeCols.kind}</th>
                </tr>
              </thead>
              <tbody>
                {p.places.map((pl, i) => (
                  <tr key={i} className={`dv-kind-${pl.kind}`}>
                    <td>
                      <span className="he" dir="rtl" lang="he">
                        {pl.e_word ?? t.absent}
                      </span>{' '}
                      {pl.e_vid !== null && (
                        <Link className="small" to={unitLink(`v:${pl.e_vid}`)}>
                          {label(pl.e_label, pl.e_label_he)}
                        </Link>
                      )}
                    </td>
                    <td>
                      <span className="he" dir="rtl" lang="he">
                        {pl.y_word ?? t.absent}
                      </span>{' '}
                      {pl.y_vid !== null && (
                        <Link className="small" to={unitLink(`v:${pl.y_vid}`)}>
                          {label(pl.y_label, pl.y_label_he)}
                        </Link>
                      )}
                    </td>
                    <td>{t.kinds[pl.kind]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  )
}

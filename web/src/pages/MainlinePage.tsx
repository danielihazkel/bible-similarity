import { Link } from 'react-router'
import { useBooks, useMainline, useMainlinePauses } from '../api/hooks'
import { isStageMissing } from '../api/client'
import type { MainlineOrder, MainlinePause, MainlineResponse } from '../api/types'
import { BookSelect, Segmented, KnownOnly } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { PrecisionNote } from '../components/PrecisionNote'
import { ErrorBox, Loading, NotComputed } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { useLocale } from '../context/localeContext'
import { readLink } from '../lib/links'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import '../i18n/pages/mainline'
import '../styles/pages/MainlinePage.css'

const PAGE_SIZE = 25
const ORDERS: MainlineOrder[] = ['longest', 'canon']

/** The narrative main line (DESIGN.md §16.91, D153): the narrator's clauses on the wayyiqtol chain
 * or off it, by book; the claim and the known pauses; the pauses themselves. */
export function MainlinePage() {
  const { m } = useLocale()
  const t = m.ml
  const res = useMainline()
  const d = res.data
  return (
    <div className="page mainline-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <PrecisionNote detector="mainline" />
      {isStageMissing(res.error) ? (
        <NotComputed>{t.noData}</NotComputed>
      ) : res.isError ? (
        <ErrorBox error={res.error} />
      ) : !d ? (
        <Loading />
      ) : (
        <>
          <Claim d={d} />
          <Books d={d} />
          <Pauses />
        </>
      )}
    </div>
  )
}

function Claim({ d }: { d: MainlineResponse }) {
  const t = useLocale().m.ml
  const c = d.claim
  return (
    <section aria-label={t.knownTitle}>
      <p className="muted small">{t.counts(d.clauses, d.main, d.background, d.pauses)}</p>
      <p>
        <span className={`dv-verdict ${c.holds ? 'holds' : 'fails'}`}>{t.verdict[c.holds ? 'holds' : 'fails']}</span>{' '}
        {t.claim(c.excess, c.null_mean, c.p.toPrecision(2), d.opening)}
      </p>
      {!c.holds && <p className="muted small">{t.claimNote}</p>}
      <p>{t.known(d.known_found, d.known.length)}</p>
      <ul className="small ml-known">
        {d.known.map((k) => (
          <li key={k.ref}>
            {k.ref}: {k.found ? t.knownFound : t.knownMissing}
          </li>
        ))}
      </ul>
    </section>
  )
}

function Books({ d }: { d: MainlineResponse }) {
  const { m, locale } = useLocale()
  const t = m.ml
  const books = useBooks()
  const named = new Map((books.data ?? []).map((b) => [b.book_id, bookName(b, locale)]))
  return (
    <section aria-labelledby="ml-books">
      <h2 id="ml-books">{t.booksTitle}</h2>
      <p className="muted small">{t.booksLede}</p>
      <TableCsv name="mainline-books">
        <table className="change-table">
          <thead>
            <tr>
              <th scope="col">{t.cols.book}</th>
              <th scope="col" className="num">
                {t.cols.main}
              </th>
              <th scope="col" className="num">
                {t.cols.background}
              </th>
              <th scope="col" className="num">
                {t.cols.share}
              </th>
              <th scope="col" className="num">
                {t.cols.pauses}
              </th>
            </tr>
          </thead>
          <tbody>
            {d.books.map((b) => (
              <tr key={b.book_id}>
                <td>{named.get(b.book_id) ?? b.book_id}</td>
                <td className="num">{b.main}</td>
                <td className="num">{b.background}</td>
                <td className="num">{t.share(b.share)}</td>
                <td className="num">{b.pauses}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableCsv>
    </section>
  )
}

function Pauses() {
  const { m, locale } = useLocale()
  const t = m.ml
  const [params, update] = useQueryParams()
  const order: MainlineOrder = params.get('order') === 'canon' ? 'canon' : 'longest'
  const bp = params.get('book')
  const book = bp === null || bp === '' ? undefined : Number(bp)
  const known = params.get('known') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useMainlinePauses({ order, book, known, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  return (
    <section aria-labelledby="ml-pauses">
      <h2 id="ml-pauses">{t.pausesTitle}</h2>
      <div className="toolbar">
        <Segmented<MainlineOrder> label={t.order.label} value={order} options={ORDERS.map((v) => ({ value: v, label: t.order[v] }))} onChange={(v) => set({ order: v === 'longest' ? null : v })} />
        <BookSelect label={m.search.book} all={m.search.allBooks} books={books.data} value={book} onChange={(v) => set({ book: v })} />
        <KnownOnly checked={known} label={t.knownOnly} onChange={(on) => set({ known: on ? '1' : null })} />
      </div>
      <PagedList csv="mainline" res={res} empty={t.none} summary={(d, p, pages) => t.pauseCount(d.total, p, pages)}>
        {(d, stale) => (
          <ol className={`hits ml-pauses ${stale}`}>
            {d.items.map((p) => (
              <PauseItem key={p.pause_id} p={p} locale={locale} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function PauseItem({ p, locale }: { p: MainlinePause; locale: 'en' | 'he' }) {
  const t = useLocale().m.ml
  const span = p.first_vid === p.last_vid
  const first = locale === 'he' ? p.first_label_he : p.first_label
  const last = locale === 'he' ? p.last_label_he : p.last_label
  const types = [...new Set(p.types.map((x) => t.types[x] ?? x))]
  const rest = p.last_vid - p.first_vid + 1 - p.verses.length
  return (
    <li className="hit ml-pause">
      <div className="hit-head">
        <span className="verse-ref">{span ? first : `${first} – ${last}`}</span>{' '}
        <span className="muted small">
          {t.pause(p.n_clauses)} · {types.join(', ')}
          {p.known && ` · ${t.namedTag}`}
        </span>
      </div>
      {p.verses.map((v) => (
        <p key={v.verse_id} className="hit-text">
          <HebrewText verse={v} />
        </p>
      ))}
      {rest > 0 && <p className="muted small">{t.more(rest)}</p>}
      <p className="small">
        <Link to={readLink(p.unit_id, '?layers=mainline')}>{t.read}</Link>
      </p>
    </li>
  )
}

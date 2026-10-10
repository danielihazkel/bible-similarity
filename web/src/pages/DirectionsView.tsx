import { Link } from 'react-router'
import { useBooks, useEchoList, useEchoes } from '../api/hooks'
import type { Book, EchoBasis, EchoBook, EchoChapter, EchoEdge, EchoesMeta } from '../api/types'
import { Segmented } from '../components/Controls'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { compareLink, unitLink } from '../lib/links'
import { bookName, bookOption, unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const BASES: EchoBasis[] = ['cited', 'borrowed', 'language', 'conflict']
const CHECKS = ['cited', 'spelling', 'borrowed'] as const

/** A direction on the cross-book echoes: citations, borrowing, then the language profile
 * (DESIGN.md §16.36). */
export function DirectionsView() {
  const { m, locale } = useLocale()
  const t = m.echo
  const res = useEchoes()
  const books = useBooks()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const byId = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  const name = (id: number) => {
    const b = byId.get(id)
    return b ? bookName(b, locale) : String(id)
  }
  const { meta } = res.data
  return (
    <>
      <h2>{t.title}</h2>
      <p className="lede">{t.lede}</p>
      {meta.bases === undefined ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Summary meta={meta} name={name} />
          <BookTable books={res.data.books} name={name} />
          <SourceTable sources={res.data.sources} />
          <EchoList books={books.data ?? []} />
        </>
      )}
    </>
  )
}

function Summary({ meta, name }: { meta: EchoesMeta; name: (id: number) => string }) {
  const t = useLocale().m.echo
  const bases = meta.bases!
  const directed = bases.cited + bases.borrowed + bases.language
  return (
    <section aria-label={t.checksTitle}>
      <p className="small">{t.summary(meta.pairs ?? 0, directed)}</p>
      <p className="small">
        {(['cited', 'borrowed', 'language', 'conflict', 'none'] as EchoBasis[]).map((b, i) => (
          <span key={b} title={t.bases[b].hint}>
            {i > 0 && ' · '}
            {t.basisCount(t.bases[b].label, bases[b])}
          </span>
        ))}
      </p>
      <h3>{t.checksTitle}</h3>
      <ul className="division-findings small">
        {CHECKS.map((k) => {
          const c = meta.checks?.[k]
          if (!c) return null
          return <li key={k}>{c.underpowered ? t.underpowered(t.check[k], c.n) : t.checkLine(t.check[k], c.agree, c.n, c.p)}</li>
        })}
        {meta.language_backward !== undefined && meta.language_forward !== undefined && (
          <li>
            {t.backward(meta.language_backward, meta.language_backward + meta.language_forward, meta.language_gap ?? 0)}{' '}
            <Link to="?view=directions&backward=1#echo-list">{t.filters.backward}</Link>
          </li>
        )}
        {meta.cycles && <li>{t.cycles(meta.cycles.map((c) => c.map(name).join(' ↔ ')))}</li>}
      </ul>
      <p className="muted small">{t.checkNote}</p>
    </section>
  )
}

function BookTable({ books, name }: { books: EchoBook[]; name: (id: number) => string }) {
  const t = useLocale().m.echo
  if (books.length === 0) return null
  return (
    <section aria-label={t.booksTitle}>
      <h3>{t.booksTitle}</h3>
      <p className="muted small">{t.booksLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
        <table className="rank-table">
          <thead>
            <tr>
              <th scope="col">{t.filters.book}</th>
              {(['cited', 'borrowed', 'language'] as const).map((b) => (
                <th key={b} scope="col" className="num" title={t.bases[b].hint}>
                  {t.bases[b].label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {books.slice(0, 30).map((b) => (
              <tr key={`${b.src_book}-${b.dst_book}`}>
                <th scope="row">{t.bookPair(name(b.src_book), name(b.dst_book))}</th>
                <td className="num">{b.cited || ''}</td>
                <td className="num">{b.borrowed || ''}</td>
                <td className="num">{b.language || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function SourceTable({ sources }: { sources: EchoChapter[] }) {
  const { m, locale } = useLocale()
  const t = m.echo
  if (sources.length === 0) return null
  return (
    <section aria-label={t.sourcesTitle}>
      <h3>{t.sourcesTitle}</h3>
      <p className="muted small">{t.sourcesLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.sourcesTitle}>
        <table className="rank-table">
          <thead>
            <tr>
              <th scope="col">{t.chapter}</th>
              <th scope="col" className="num">
                {t.explicit}
              </th>
              <th scope="col" className="num">
                {t.lends}
              </th>
              <th scope="col" className="num">
                {t.borrows}
              </th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.unit.unit_id}>
                <th scope="row">
                  <Link to={`?view=directions&unit=${encodeURIComponent(s.unit.unit_id)}#echo-list`}>{unitLabel(s.unit, locale)}</Link>
                </th>
                <td className="num">{s.lends_explicit}</td>
                <td className="num">{s.lends}</td>
                <td className="num">{s.borrows}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function EchoList({ books }: { books: Book[] }) {
  const { m, locale } = useLocale()
  const t = m.echo
  const [params, update] = useQueryParams()
  const bp = params.get('basis')
  const basis = BASES.includes(bp as EchoBasis) ? (bp as EchoBasis) : undefined
  const backward = params.get('backward') === '1' ? true : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const res = useEchoList({
    basis,
    // a conflict has no direction; otherwise only the directed pairs are listed
    directed: basis ? undefined : true,
    backward,
    book,
    unit,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.listTitle} id="echo-list">
      <h3>{t.listTitle}</h3>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented<string>
          label={t.filters.basis}
          value={basis ?? ''}
          options={[
            { value: '', label: t.filters.any },
            ...BASES.map((b) => ({ value: b, label: t.bases[b].label, title: t.bases[b].hint })),
          ]}
          onChange={(v) => set({ basis: v || null })}
        />
        <label className="control">
          <span>{t.filters.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.par.allBooks}</option>
            {books.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={backward === true} onChange={(e) => set({ backward: e.target.checked ? '1' : null })} />
          {t.filters.backward}
        </label>
      </div>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>
          {t.none}
        </EmptyList>
      ) : (
        <>
          <p className="muted small">{t.page(res.data.total, page, pages)}</p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((e) => (
              <EchoItem key={e.edge_id} e={e} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </section>
  )
}

function EchoItem({ e }: { e: EchoEdge }) {
  const { m, locale } = useLocale()
  const t = m.echo
  const [src, dst] = e.direction < 0 ? [e.b, e.a] : [e.a, e.b]
  return (
    <li className="disc echo-item">
      <div className="hit-head">
        <span>
          <Link to={unitLink(src.unit_id)}>{unitLabel(src, locale)}</Link> {e.direction === 0 ? '↔' : t.arrow}{' '}
          <Link to={unitLink(dst.unit_id)}>{unitLabel(dst, locale)}</Link>
        </span>
        <span className="phrase-tag" title={t.bases[e.basis].hint}>
          {t.bases[e.basis].label}
        </span>
        {e.direction < 0 && <span className="small q-strong">{t.againstCanon}</span>}
        {e.n_cited > 0 && <span className="muted small">{t.cited(e.n_cited)}</span>}
        {e.gap !== null && (
          <span className="muted small" title={t.gapTitle}>
            {t.gap(e.direction < 0 ? -e.gap : e.gap)}
          </span>
        )}
        <span className="hit-actions">
          <Link className="linkish" to={compareLink(e.a.unit_id, e.b.unit_id)}>
            {t.compare}
          </Link>
        </span>
      </div>
    </li>
  )
}

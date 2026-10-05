import { Link, useParams } from 'react-router'
import { useBooks, useDomain, useDomains } from '../api/hooks'
import type { DomainInfo } from '../api/types'
import { DomainChip, DomainName } from '../components/DomainName'
import { HebrewText } from '../components/HebrewText'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { domainLink, unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** `/domains`: the domain tree; `/domains/:code`: one domain's verses (DESIGN.md §16.22). */
export function DomainsPage() {
  const code = useParams().code
  return code ? <DomainVerses code={code} /> : <DomainTree />
}

/** The two top levels as sections, the third as chips (deeper levels on each domain's page). */
function DomainTree() {
  const { m } = useLocale()
  const t = m.dom
  const doms = useDomains()
  if (doms.isPending) return <Loading />
  if (doms.error) return <ErrorBox error={doms.error} />
  const children = new Map<string, DomainInfo[]>()
  for (const d of doms.data) {
    if (d.parent !== null) children.set(d.parent, [...(children.get(d.parent) ?? []), d])
  }
  const tops = doms.data.filter((d) => d.level === 1)
  return (
    <div className="page domains-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">{t.source}</p>
      {tops.length === 0 && <p className="status">{t.noLexicon}</p>}
      {tops.map((top) => (
        <section key={top.code} className="domain-top" aria-labelledby={`dom-${top.code}`}>
          <h2 id={`dom-${top.code}`}>
            <Link to={domainLink(top.code)}>
              <DomainName domain={top} />
            </Link>{' '}
            <span className="muted small">{t.verses(top.n_verses)}</span>
          </h2>
          {(children.get(top.code) ?? []).map((mid) => (
            <div key={mid.code} className="domain-mid">
              <h3>
                <Link to={domainLink(mid.code)}>
                  <DomainName domain={mid} />
                </Link>{' '}
                <span className="muted small">{t.verses(mid.n_verses)}</span>
              </h3>
              <div className="chips">
                {(children.get(mid.code) ?? []).filter((d) => d.n_verses > 0).map((d) => (
                  <DomainChip key={d.code} domain={d} extra={m.num(d.n_verses)} title={t.open(d.label_en)} />
                ))}
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  )
}

/** A domain concordance: its path, subdomains, books and verses (words in it highlighted). */
function DomainVerses({ code }: { code: string }) {
  const { m, locale } = useLocale()
  const t = m.dom
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useDomain(code, book, PAGE_SIZE, (page - 1) * PAGE_SIZE)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />

  const d = res.data
  const names = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  const most = Math.max(1, ...d.by_book.map((b) => b.n_verses))
  const pages = Math.max(1, Math.ceil(d.total / PAGE_SIZE))
  return (
    <div className="page domains-page">
      <nav className="crumbs muted small" aria-label={t.broader}>
        <Link to="/domains">{t.title}</Link>
        {d.path.map((p) => (
          <span key={p.code}>
            {' › '}
            <Link to={domainLink(p.code)}>
              <DomainName domain={p} />
            </Link>
          </span>
        ))}
      </nav>
      <h1>
        <DomainName domain={d.domain} />
      </h1>
      <p className="lede">{t.occurrences(d.domain.weight, d.domain.n_verses, d.by_book.length)}</p>

      {d.children.length > 0 && (
        <section aria-label={t.subdomains}>
          <h2>{t.subdomains}</h2>
          <div className="chips">
            {d.children.filter((c) => c.n_verses > 0).map((c) => (
              <DomainChip key={c.code} domain={c} extra={m.num(c.n_verses)} title={t.open(c.label_en)} />
            ))}
          </div>
        </section>
      )}

      <section aria-label={t.byBook}>
        <h2>{t.byBook}</h2>
        <ul className="book-bars">
          {d.by_book.map((b) => {
            const on = book === b.book_id
            return (
              <li key={b.book_id}>
                <button
                  type="button"
                  className={on ? 'on' : undefined}
                  aria-pressed={on}
                  onClick={() => update({ book: on ? null : String(b.book_id), page: null })}
                  title={on ? m.concordance.allBooks : m.concordance.onlyBook}
                >
                  <span className="bar-label">{names.has(b.book_id) ? bookName(names.get(b.book_id)!, locale) : b.book_id}</span>
                  <span className="bar-track">
                    <span className="bar-fill" style={{ width: `${(b.n_verses / most) * 100}%` }} />
                  </span>
                  <span className="bar-n">{b.n_verses}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      <h2>
        {book !== undefined && names.get(book) ? t.versesIn(bookName(names.get(book)!, locale)) : t.allVerses}{' '}
        <span className="muted small">({m.num(d.total)})</span>
      </h2>
      {d.items.length === 0 ? (
        <EmptyList total={d.total} limit={d.limit}>{t.empty}</EmptyList>
      ) : (
        <ol className={`hits ${res.isPlaceholderData ? 'stale' : ''}`}>
          {d.items.map((h) => (
            <li key={h.verse.verse_id} className="hit">
              <div className="hit-head">
                <Link className="hit-ref" to={unitLink(`v:${h.verse.verse_id}`)}>
                  <UnitName en={h.label_en} he={h.label_he} />
                </Link>
              </div>
              <p className="hit-text">
                <HebrewText verse={h.verse} highlight={new Map(h.display_idxs.map((i) => [i, 'shared'])) as Highlight} />
              </p>
            </li>
          ))}
        </ol>
      )}
      <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
    </div>
  )
}

import { Link } from 'react-router'
import { useBooks, useCitationList, useCitations } from '../api/hooks'
import type { Book, Citation, CitationBook, CitationFamily, CitationsMeta } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { compareLink, unitLink } from '../lib/links'
import { bookName, bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20
const FAMILIES: CitationFamily[] = ['written', 'word', 'command']

/** Verses that say they quote or fulfil another, with their sources (DESIGN.md §16.31). */
export function CitationsPage() {
  const { m, locale } = useLocale()
  const t = m.cit
  const res = useCitations()
  const books = useBooks()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { meta } = res.data
  const byId = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  const name = (id: number) => {
    const b = byId.get(id)
    return b ? bookName(b, locale) : String(id)
  }
  return (
    <div className="page citations-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {meta.citations === undefined ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Summary meta={meta} />
          <BookGraph books={res.data.books} name={name} />
          <CitationList books={books.data ?? []} name={name} />
        </>
      )}
    </div>
  )
}

function Summary({ meta }: { meta: CitationsMeta }) {
  const t = useLocale().m.cit
  const g = meta.gold
  return (
    <section>
      <p className="small">{t.summary(meta.citations ?? 0, meta.resolved ?? 0)}</p>
      <ul className="division-findings small">
        {FAMILIES.map((f) => {
          const s = meta.families?.[f]
          return s && s.verses > 0 && s.share != null && s.null_share != null ? (
            <li key={f} title={t.families[f].hint}>
              {t.familyLine(t.families[f].label, s.resolved, s.verses, s.share, s.null_share, s.p)}
            </li>
          ) : null
        })}
        {g && g.found > 0 && <li>{t.gold(g.top1, g.found, g.top_k, g.k, g.resolved_right, g.resolved)}</li>}
        {meta.word_lag_median != null && <li>{t.lag(Math.round(meta.word_lag_median))}</li>}
      </ul>
      <p className="muted small">{t.familyNote}</p>
    </section>
  )
}

function BookGraph({ books, name }: { books: CitationBook[]; name: (id: number) => string }) {
  const t = useLocale().m.cit
  if (books.length === 0) return null
  return (
    <section aria-label={t.booksTitle}>
      <h2>{t.booksTitle}</h2>
      <p className="muted small">{t.booksLede}</p>
      <ul className="cite-books">
        {books.map((b) => (
          <li key={`${b.book_id}-${b.target_book}`}>
            <Link to={`?book=${b.book_id}&resolved=1#citation-list`}>{t.bookPair(name(b.book_id), name(b.target_book), b.n)}</Link>
          </li>
        ))}
      </ul>
    </section>
  )
}

function CitationList({ books, name }: { books: Book[]; name: (id: number) => string }) {
  const { m, locale } = useLocale()
  const t = m.cit
  const [params, update] = useQueryParams()
  const fp = params.get('family')
  const family = FAMILIES.includes(fp as CitationFamily) ? (fp as CitationFamily) : undefined
  const resolved = params.get('resolved') === '1' ? true : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const res = useCitationList({ family, resolved, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.listTitle} id="citation-list">
      <h2>{t.listTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented<string>
          label={t.filters.family}
          value={family ?? ''}
          options={[
            { value: '', label: t.filters.any },
            ...FAMILIES.map((f) => ({ value: f, label: t.families[f].label, title: t.families[f].hint })),
          ]}
          onChange={(v) => set({ family: v || null })}
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
          <input type="checkbox" checked={resolved === true} onChange={(e) => set({ resolved: e.target.checked ? '1' : null })} />
          {t.filters.resolved}
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
            {res.data.items.map((c) => (
              <CitationItem key={c.cite_id} c={c} book={name(c.book_id)} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </section>
  )
}

function CitationItem({ c, book }: { c: Citation; book: string }) {
  const { m, locale } = useLocale()
  const t = m.cit
  const label = (en: string | null, he: string | null) => (locale === 'he' ? he : en) ?? ''
  return (
    <li className="disc cite-item">
      <div className="hit-head">
        <Link to={unitLink(`v:${c.verse_id}`)}>{label(c.label, c.label_he)}</Link>
        <span className="muted small">{book}</span>
        <span className="phrase-tag" title={t.families[c.family].hint}>
          {t.families[c.family].label}
        </span>
        <span className={`small ${c.resolved ? 'q-strong' : 'muted'}`}>{c.resolved ? t.resolvedTag : t.unresolvedTag}</span>
        {c.named && <span className="muted small">{t.namedTag(c.gold_rank)}</span>}
        {c.target_label && (
          <span className="hit-actions">
            <Link className="linkish" to={compareLink(`v:${c.verse_id}`, `v:${c.target?.verse_id}`)}>
              {t.compare}
            </Link>
          </span>
        )}
      </div>
      <HebrewText verse={c.verse} />
      {c.target && (
        <div className="cite-source">
          <p className="small">
            {t.source}: <Link to={unitLink(`v:${c.target.verse_id}`)}>{label(c.target_label, c.target_label_he)}</Link>
          </p>
          <HebrewText verse={c.target} className="cite-source-text" />
        </div>
      )}
      {c.candidates.length > 1 && (
        <p className="muted small">
          {t.others}{' '}
          {c.candidates.slice(1).map((x, i) => (
            <span key={x.verse_id}>
              {i > 0 && ' · '}
              <Link to={unitLink(`v:${x.verse_id}`)}>{label(x.label, x.label_he)}</Link>
            </span>
          ))}
        </p>
      )}
    </li>
  )
}

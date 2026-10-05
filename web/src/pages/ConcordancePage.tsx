import { Link, useParams } from 'react-router'
import { useBooks, useLemma } from '../api/hooks'
import { ExportCsv } from '../components/ExportCsv'
import { HebrewText } from '../components/HebrewText'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import { bookName } from '../lib/names'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** Every verse containing one content lemma, with its distribution over the books. */
export function ConcordancePage() {
  const { m, locale } = useLocale()
  const lemma = useParams().lemma!
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const conc = useLemma(lemma, book, PAGE_SIZE, (page - 1) * PAGE_SIZE)
  if (conc.isPending) return <Loading />
  if (conc.error) return <ErrorBox error={conc.error} />

  const c = conc.data
  const names = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  const most = Math.max(...c.by_book.map((b) => b.n_verses))
  const pages = Math.max(1, Math.ceil(c.total / PAGE_SIZE))
  return (
    <div className="page concordance-page">
      <h1>
        <span className="he-label big" dir="rtl" lang="he">
          {c.he_lemma}
        </span>{' '}
        <span className="type-tag">{m.lemmas.strongsTag(c.lemma)}</span>
      </h1>
      <p className="lede">
        {m.concordance.occurrences(c.n_words, c.n_verses, c.by_book.length)}
      </p>

      <section aria-label={m.concordance.byBook}>
        <h2>{m.concordance.byBook}</h2>
        <ul className="book-bars">
          {c.by_book.map((b) => {
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
        {book !== undefined && names.get(book)
          ? m.concordance.versesIn(bookName(names.get(book)!, locale))
          : m.concordance.verses}{' '}
        <span className="muted small">({m.num(c.total)})</span>
      </h2>
      <p className="muted small">
        <ExportCsv
          filename={`concordance-${lemma}-p${page}.csv`}
          rows={() => c.items.map((h) => ({ verse: h.label_en, reference: h.label_he, text: h.verse.text_display }))}
          all={{ list: 'concordance', params: { lemma, book } }}
        />
      </p>
      <ol className={`hits ${conc.isPlaceholderData ? 'stale' : ''}`}>
        {c.items.map((h) => (
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
      <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
    </div>
  )
}

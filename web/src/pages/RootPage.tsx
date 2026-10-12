import { Link, useParams } from 'react-router'
import { useBooks, useRootFamily } from '../api/hooks'
import { HebrewText } from '../components/HebrewText'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { lemmaLink, unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** A root family (§16.38): its words, with how Strong's derives them, and every verse holding any. */
export function RootPage() {
  const { m, locale } = useLocale()
  const t = m.root
  const root = useParams().root!
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useRootFamily(root, { book, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const f = res.data
  const names = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  const most = Math.max(...f.by_book.map((b) => b.n_verses))
  const pages = Math.max(1, Math.ceil(f.total / PAGE_SIZE))
  return (
    <div className="page concordance-page root-page">
      <h1>
        {t.familyTitle('')}
        <span className="he-label big" dir="rtl" lang="he">
          {f.root_he}
        </span>{' '}
        <span className="type-tag">{m.lemmas.strongsTag(f.root)}</span>
      </h1>
      <p className="lede">{t.familyLede(f.members.length, f.n_verses)}</p>
      <div className="chips root-members">
        {f.members.map((l) => (
          <Link key={l.lemma} className="chip lemma-chip" to={lemmaLink(l.lemma)} title={m.lemmas.allVerses(l.lemma)}>
            <span dir="rtl" lang="he">
              {l.he_lemma}
            </span>{' '}
            <span className="small">
              {m.word.verses(l.n_verses)}
              {f.links[l.lemma] && <> {t.link(f.links[l.lemma])}</>}
            </span>
          </Link>
        ))}
      </div>
      <section aria-label={m.concordance.byBook}>
        <h2>{m.concordance.byBook}</h2>
        <ul className="book-bars">
          {f.by_book.map((b) => {
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
        {t.verses(f.total)}
        {book !== undefined && names.get(book) ? t.inBook(bookName(names.get(book)!, locale)) : ''}
      </h2>
      <ol className={`hits ${res.isPlaceholderData ? 'stale' : ''}`}>
        {f.items.map((h) => (
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

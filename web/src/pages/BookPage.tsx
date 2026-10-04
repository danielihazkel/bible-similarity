import { Link, useParams } from 'react-router'
import { useBooks, useUnit, useUnits } from '../api/hooks'
import type { Book, UnitType } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

type Tab = 'chapters' | 'verses' | 'parashot' | 'pericopes'
const TAB_TYPE: Partial<Record<Tab, UnitType>> = { parashot: 'parasha', pericopes: 'pericope' }

export function BookPage() {
  const bookId = Number(useParams().bookId)
  const [params, update] = useQueryParams()
  const books = useBooks()
  const book = books.data?.find((b) => b.book_id === bookId)
  const isTorah = book?.section === 'Torah'
  const tabs: Tab[] = isTorah ? ['chapters', 'verses', 'parashot', 'pericopes'] : ['chapters', 'verses', 'pericopes']
  const raw = params.get('tab') as Tab | null
  const tab: Tab = raw && tabs.includes(raw) ? raw : 'chapters'
  const listType = TAB_TYPE[tab]
  const units = useUnits(listType ?? 'chapter', book && listType ? bookId : undefined)

  if (books.isPending) return <Loading />
  if (books.error) return <ErrorBox error={books.error} />
  if (!book) return <p className="status error">Unknown book.</p>

  return (
    <div className="page">
      <p className="crumbs">
        <Link to="/">Books</Link> › {book.section}
      </p>
      <h1>
        {book.name}{' '}
        <span className="he-label big" dir="rtl" lang="he">
          {book.he_name}
        </span>
      </h1>
      <Segmented
        label="Unit type"
        value={tab}
        onChange={(t) => update({ tab: t === 'chapters' ? null : t, ...(t !== 'verses' && { ch: null }) })}
        options={tabs.map((t) => ({ value: t, label: t[0].toUpperCase() + t.slice(1) }))}
      />
      {tab === 'chapters' ? (
        <ul className="chapter-grid">
          {/* chapter unit ids are `c:{book_id}:{chapter}` */}
          {Array.from({ length: book.n_chapters }, (_, i) => i + 1).map((n) => (
            <li key={n}>
              <Link to={unitLink(`c:${book.book_id}:${n}`)}>{n}</Link>
            </li>
          ))}
        </ul>
      ) : tab === 'verses' ? (
        <VerseBrowser book={book} chapter={params.get('ch')} onChapter={(n) => update({ ch: String(n) })} />
      ) : units.isPending ? (
        <Loading />
      ) : units.error ? (
        <ErrorBox error={units.error} />
      ) : (
        <ul className="unit-list">
          {units.data.map((u) => (
            <li key={u.unit_id}>
              <Link to={unitLink(u.unit_id)}>
                <span className="unit-en">{u.label_en}</span>
                {tab === 'parashot' && (
                  <span className="he-label" dir="rtl" lang="he">
                    {u.label_he}
                  </span>
                )}
                <span className="muted small">
                  {u.n_verses} {u.n_verses === 1 ? 'verse' : 'verses'}
                  {u.marker && ` · ${u.marker === 'pe' ? 'פ open' : 'ס closed'}`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Chapter picker → that chapter's verses with their text, each linking to the verse unit page. */
function VerseBrowser({ book, chapter, onChapter }: { book: Book; chapter: string | null; onChapter: (n: number) => void }) {
  const n = Number(chapter)
  const ch = Number.isInteger(n) && n >= 1 && n <= book.n_chapters ? n : 1
  const detail = useUnit(`c:${book.book_id}:${ch}`)

  return (
    <>
      <ul className="chapter-grid" aria-label="Chapter">
        {Array.from({ length: book.n_chapters }, (_, i) => i + 1).map((c) => (
          <li key={c}>
            <button type="button" aria-current={c === ch || undefined} onClick={() => onChapter(c)}>
              {c}
            </button>
          </li>
        ))}
      </ul>
      <h2>Chapter {ch}</h2>
      {detail.isPending ? (
        <Loading />
      ) : detail.error ? (
        <ErrorBox error={detail.error} />
      ) : (
        <ol className="verse-list source" aria-label="Verses">
          {detail.data.verses.map((v) => (
            <li key={v.verse_id}>
              <Link className="verse-num" to={unitLink(`v:${v.verse_id}`)} title={`${v.ref}: similar verses`}>
                {v.verse}
              </Link>
              <Link className="verse-link" to={unitLink(`v:${v.verse_id}`)} tabIndex={-1}>
                <HebrewText verse={v} />
              </Link>
            </li>
          ))}
        </ol>
      )}
    </>
  )
}

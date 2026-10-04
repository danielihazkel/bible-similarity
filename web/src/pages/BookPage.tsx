import { Link, useParams } from 'react-router'
import { useBooks, useUnits } from '../api/hooks'
import type { UnitType } from '../api/types'
import { Segmented } from '../components/Controls'
import { ErrorBox, Loading } from '../components/Status'
import { unitLink } from '../lib/links'
import { useQueryParams } from '../lib/urlState'

type Tab = 'chapters' | 'parashot' | 'pericopes'
const TAB_TYPE: Record<Tab, UnitType> = { chapters: 'chapter', parashot: 'parasha', pericopes: 'pericope' }

export function BookPage() {
  const bookId = Number(useParams().bookId)
  const [params, update] = useQueryParams()
  const books = useBooks()
  const book = books.data?.find((b) => b.book_id === bookId)
  const isTorah = book?.section === 'Torah'
  const tabs: Tab[] = isTorah ? ['chapters', 'parashot', 'pericopes'] : ['chapters', 'pericopes']
  const raw = params.get('tab') as Tab | null
  const tab: Tab = raw && tabs.includes(raw) ? raw : 'chapters'
  const units = useUnits(TAB_TYPE[tab], book ? bookId : undefined)

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
        onChange={(t) => update({ tab: t === 'chapters' ? null : t })}
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

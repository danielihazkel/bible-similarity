import { Link } from 'react-router'
import { useBooks } from '../api/hooks'
import type { Book } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'
import { useT } from '../context/localeContext'
import { CATALOGS } from '../i18n'

export function BooksPage() {
  const m = useT()
  const { data, error, isPending } = useBooks()
  if (isPending) return <Loading />
  if (error) return <ErrorBox error={error} />
  const sections = new Map<string, Book[]>()
  for (const b of data) sections.set(b.section, [...(sections.get(b.section) ?? []), b])
  return (
    <div className="page">
      <h1>{m.books.title}</h1>
      <p className="lede">{m.books.lede}</p>
      <p>
        <Link to="/findings" className="findings-link">
          {m.books.findings} {m.locale === 'he' ? '←' : '→'}
        </Link>
      </p>
      {[...sections].map(([section, books]) => (
        <section key={section} className="section">
          <h2>
            {m.units.sections[section] ?? section}
            {m.locale === 'en' && (
              <>
                {' '}
                <span className="he-label" dir="rtl" lang="he">
                  {CATALOGS.he.units.sections[section]}
                </span>
              </>
            )}
          </h2>
          <ul className="book-grid">
            {books.map((b) => (
              <li key={b.book_id}>
                <Link to={`/browse/${b.book_id}`} className="book-card">
                  <span className="he book-he" dir="rtl" lang="he">
                    {b.he_name}
                  </span>
                  {m.locale === 'en' && <span className="book-en">{b.name}</span>}
                  <span className="muted small">{m.units.chaptersShort(b.n_chapters)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

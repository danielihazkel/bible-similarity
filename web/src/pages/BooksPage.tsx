import { Link } from 'react-router'
import { useBooks } from '../api/hooks'
import type { Book } from '../api/types'
import { ErrorBox, Loading } from '../components/Status'

const SECTION_HE: Record<string, string> = { Torah: 'תורה', Prophets: 'נביאים', Writings: 'כתובים' }

export function BooksPage() {
  const { data, error, isPending } = useBooks()
  if (isPending) return <Loading />
  if (error) return <ErrorBox error={error} />
  const sections = new Map<string, Book[]>()
  for (const b of data) sections.set(b.section, [...(sections.get(b.section) ?? []), b])
  return (
    <div className="page">
      <h1>Browse</h1>
      <p className="lede">
        Pick a book, then a chapter, parasha or pericope. Every unit lists its most similar units by shared wording,
        meaning, or both.
      </p>
      {[...sections].map(([section, books]) => (
        <section key={section} className="section">
          <h2>
            {section}{' '}
            <span className="he-label" dir="rtl" lang="he">
              {SECTION_HE[section]}
            </span>
          </h2>
          <ul className="book-grid">
            {books.map((b) => (
              <li key={b.book_id}>
                <Link to={`/browse/${b.book_id}`} className="book-card">
                  <span className="he book-he" dir="rtl" lang="he">
                    {b.he_name}
                  </span>
                  <span className="book-en">{b.name}</span>
                  <span className="muted small">{b.n_chapters} ch.</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

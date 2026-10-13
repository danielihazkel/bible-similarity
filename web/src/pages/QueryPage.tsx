import { useState } from 'react'
import { Link } from 'react-router'
import { patternParams, useBooks, usePatterns } from '../api/hooks'
import type { PatternProblem, PatternVerse } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { UnitFilter } from '../components/UnitFilter'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20

/** Pattern search (§16.46): a query over lemmas, roots, morphology and syntax, word by word. */
export function QueryPage() {
  const { m } = useLocale()
  const t = m.qry
  const [params, update] = useQueryParams()
  const q = params.get('q') ?? ''
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') ?? undefined
  const page = parsePage(params.get('page'))
  const query = { q, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = usePatterns(query)
  const run = (text: string) => update({ q: text.trim() || null, page: null }, false)
  return (
    <div className="page query-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <QueryForm key={q} initial={q} onSubmit={run} />
      {unit && <UnitFilter unitId={unit} onClear={() => update({ unit: null, page: null })} />}
      {!q ? (
        <p className="status">{t.prompt}</p>
      ) : res.data?.error ? (
        <Problem query={res.data.q} error={res.data.error} />
      ) : (
        <>
          {res.data && res.data.books.length > 0 && (
            <ByBook books={res.data.books} book={book} onBook={(b) => update({ book: b === undefined ? null : String(b), page: null })} />
          )}
          <PagedList
            res={res}
            empty={t.empty}
            summary={(d, p, pages) => (
              <>
                {t.summary(d.matches, d.total)} · {m.pat.pageOf(p, pages)}
                {' · '}
                <ExportCsv
                  all={{ list: 'patterns', params: patternParams(query) }}
                  filename={`patterns-p${p}.csv`}
                  rows={() => d.items.map((v) => ({ verse: v.label, words: v.text, matches: v.matches.length }))}
                />
              </>
            )}
          >
            {(d, stale) => (
              <ol className={`hits ${stale}`}>
                {d.items.map((v) => (
                  <Hit key={v.verse_id} v={v} />
                ))}
              </ol>
            )}
          </PagedList>
        </>
      )}
      <Examples onPick={run} />
      <Help />
    </div>
  )
}

function QueryForm({ initial, onSubmit }: { initial: string; onSubmit: (text: string) => void }) {
  const t = useLocale().m.qry
  const [draft, setDraft] = useState(initial)
  return (
    <form
      className="search-form"
      role="search"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(draft)
      }}
    >
      <input
        className="search-input query-input"
        dir="ltr"
        type="search"
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder={t.placeholder}
        aria-label={t.inputLabel}
      />
      <button type="submit" className="primary">
        {t.run}
      </button>
    </form>
  )
}

/** What went wrong with the query, its place marked. */
function Problem({ query, error }: { query: string; error: PatternProblem }) {
  const t = useLocale().m.qry
  const end = Math.min(query.length, error.at + Math.max(error.token.length, 1))
  return (
    <div className="status error query-problem" role="alert">
      <p>{t.errors[error.code](error.token)}</p>
      {query && (
        <p className="query-code" dir="ltr">
          <code>
            {query.slice(0, error.at)}
            <mark title={t.at(error.at)}>{query.slice(error.at, end) || ' '}</mark>
            {query.slice(end)}
          </code>
        </p>
      )}
    </div>
  )
}

function ByBook({ books, book, onBook }: { books: { book_id: number; matches: number }[]; book: number | undefined; onBook: (b: number | undefined) => void }) {
  const { m, locale } = useLocale()
  const t = m.qry
  const all = useBooks()
  const name = new Map((all.data ?? []).map((b) => [b.book_id, bookName(b, locale)]))
  return (
    <section aria-label={t.byBook} className="query-books">
      <span className="muted small">{t.byBook}: </span>
      {book !== undefined && (
        <button type="button" className="chip" onClick={() => onBook(undefined)}>
          {t.allBooks}
        </button>
      )}
      {books.map((b) => (
        <button
          key={b.book_id}
          type="button"
          className={`chip${b.book_id === book ? ' on' : ''}`}
          aria-pressed={b.book_id === book}
          onClick={() => onBook(b.book_id === book ? undefined : b.book_id)}
        >
          {t.bookCount(name.get(b.book_id) ?? String(b.book_id), b.matches)}
        </button>
      ))}
    </section>
  )
}

function Hit({ v }: { v: PatternVerse }) {
  const t = useLocale().m.qry
  const hl: Highlight = new Map()
  for (const match of v.matches) for (const i of match.tokens) if (i !== null) hl.set(i, 'shared')
  return (
    <li className="hit query-hit">
      <div className="hit-head">
        <Link className="verse-ref" to={unitLink(`v:${v.verse_id}`)}>
          <UnitName en={v.label} he={v.label_he} />
        </Link>{' '}
        <span className="muted small" dir="rtl" lang="he">
          {v.text}
        </span>{' '}
        <Link className="small" to={unitLink(v.unit_id)}>
          {t.read}
        </Link>
      </div>
      <p className="hit-text">
        <HebrewText verse={v.verse} highlight={hl} />
      </p>
    </li>
  )
}

function Examples({ onPick }: { onPick: (q: string) => void }) {
  const t = useLocale().m.qry
  return (
    <section aria-label={t.examplesTitle}>
      <h2>{t.examplesTitle}</h2>
      <ul className="query-examples">
        {t.examples.map((e) => (
          <li key={e.q}>
            <button type="button" className="linkish" onClick={() => onPick(e.q)}>
              <code dir="ltr">{e.q}</code>
            </button>{' '}
            <span className="muted small">{e.text}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Help() {
  const t = useLocale().m.qry
  return (
    <details className="query-help">
      <summary>{t.helpTitle}</summary>
      <ul>
        {t.syntax.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.keysCaption}>
        <table className="change-table">
          <caption>{t.keysCaption}</caption>
          <thead>
            <tr>
              <th>{t.keyCols.key}</th>
              <th>{t.keyCols.values}</th>
              <th>{t.keyCols.meaning}</th>
            </tr>
          </thead>
          <tbody>
            {t.keys.map((k) => (
              <tr key={k.key}>
                <td>
                  <code>{k.key}</code>
                </td>
                <td dir="ltr">{k.values}</td>
                <td>{k.meaning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

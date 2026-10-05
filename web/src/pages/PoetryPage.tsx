import { Link } from 'react-router'
import { useBooks, useParallelism } from '../api/hooks'
import type { ParallelBook, UnitType } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { Segmented } from '../components/Controls'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { unitTypeLabel } from '../lib/format'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'
import { WordPairsView } from './WordPairsView'

const PAGE_SIZE = 50
const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha']
const pct = (x: number | null) => (x === null ? '—' : `${Math.round(x * 100)}%`)

/** Where verses split into parallel halves: poetry by the te'amim, including poems inside prose. */
export function PoetryPage() {
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'pairs' ? 'pairs' : 'units'
  return (
    <div className="page poetry-page">
      <h1>Parallel halves</h1>
      <div className="toolbar">
        <Segmented
          label="View"
          value={view}
          onChange={(v) => update({ view: v === 'units' ? null : v, page: null })}
          options={[
            { value: 'units', label: 'Parallel verses' },
            { value: 'pairs', label: 'Word pairs' },
          ]}
        />
      </div>
      {view === 'pairs' ? <WordPairsView /> : <UnitsView />}
    </div>
  )
}

function UnitsView() {
  const [params, update] = useQueryParams()
  const raw = params.get('type') as UnitType | null
  const unitType = raw && TYPES.includes(raw) ? raw : 'chapter'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const excludePoetic = params.get('all') !== '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useParallelism({ unitType, book, excludePoetic, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const name = new Map(books.data?.map((b) => [b.book_id, b.name]) ?? [])
  const auc = res.data ? Object.values(res.data.held_out_auc) : []

  return (
    <>
      <p className="lede">
        The accents divide every verse at its main pause (etnahta; oleh-ve-yored in Psalms, Proverbs and Job). In poetry the
        two halves restate each other: similar meaning, other words, the same grammar, balanced length. A model trained only
        on how the halves relate — Psalms, Proverbs and Job against narrative and law — scores every verse; the share of
        parallel verses shows poetry wherever it is, including poems embedded in prose.
      </p>
      {auc.length > 0 && (
        <p className="muted small">
          Held-out accuracy (AUC on a poetic book the model did not see): {auc.map((a) => a.toFixed(2)).join(' · ')}
        </p>
      )}

      {res.data && <BookBars books={res.data.books} name={name} onPick={(b) => set({ book: String(b) })} />}

      <div className="toolbar">
        <Segmented
          label="Unit type"
          value={unitType}
          onChange={(t) => set({ type: t === 'chapter' ? null : t })}
          options={TYPES.map((t) => ({ value: t, label: unitTypeLabel(t) }))}
        />
        <label className="control">
          <span>Book</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">All books</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {b.name} · {b.he_name}
              </option>
            ))}
          </select>
        </label>
        <label className="check" title="Psalms, Proverbs and Job: the books the model learned from">
          <input type="checkbox" checked={!excludePoetic} onChange={(e) => set({ all: e.target.checked ? '1' : null })} />
          Include Psalms, Proverbs, Job
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No units match these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} {unitTypeLabel(unitType).toLowerCase()}s, most parallel first · page {page} of{' '}
            {pages}
            {' · '}
            <ExportCsv
              filename={`parallel-halves-${unitType}-p${page}.csv`}
              rows={() =>
                res.data.items.map((r) => ({
                  unit: r.unit.label_en,
                  share_parallel: r.share_parallel,
                  mean_prob: r.mean_prob,
                  verses: r.n_scored,
                }))
              }
            />
          </p>
          <div className="table-wrap">
            <table className={`change-table ${res.isPlaceholderData ? 'stale' : ''}`}>
              <thead>
                <tr>
                  <th>{unitTypeLabel(unitType)}</th>
                  <th className="num" title="Verses whose halves score as parallel">
                    Parallel verses
                  </th>
                  <th className="num" title="Mean probability over the unit's verses">
                    Mean
                  </th>
                  <th className="num">Verses</th>
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((r) => (
                  <tr key={r.unit.unit_id}>
                    <td>
                      <Link to={unitLink(r.unit.unit_id, '?halves=1')}>{r.unit.label_en}</Link>{' '}
                      <span className="he-label" dir="rtl" lang="he">
                        {r.unit.label_he}
                      </span>
                    </td>
                    <td className="num">{pct(r.share_parallel)}</td>
                    <td className="num">{r.mean_prob.toFixed(2)}</td>
                    <td className="num">{r.n_scored}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </>
  )
}

function BookBars({ books, name, onPick }: { books: ParallelBook[]; name: Map<number, string>; onPick: (b: number) => void }) {
  return (
    <section aria-label="Parallel verses per book">
      <h2>By book</h2>
      <p className="muted small">Share of each book's verses with parallel halves; green = the poetic-accent books.</p>
      <ul className="book-bars">
        {books.map((b) => (
          <li key={b.book_id} className={b.poetic_accents ? 'poetic' : undefined}>
            <button type="button" className="linkish" onClick={() => onPick(b.book_id)}>
              {name.get(b.book_id) ?? b.book_id}
            </button>
            <span className="bar-track" aria-hidden="true">
              <span className="bar-fill" style={{ width: `${(b.share_parallel ?? 0) * 100}%` }} />
            </span>
            <span className="num small">{pct(b.share_parallel)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

import { Link } from 'react-router'
import { useBooks, useParallelism, parallelismParams } from '../api/hooks'
import type { ParallelBook, UnitType } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { Segmented } from '../components/Controls'
import { PagedList } from '../components/Pager'
import { useLocale, useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { bookName, bookOption, unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { WordPairsView } from './WordPairsView'

const PAGE_SIZE = 50
const TYPES: UnitType[] = ['chapter', 'pericope', 'parasha']
const pct = (x: number | null) => (x === null ? '—' : `${Math.round(x * 100)}%`)

/** Where verses split into parallel halves: poetry by the te'amim, including poems inside prose. */
export function PoetryPage() {
  const m = useT()
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'pairs' ? 'pairs' : 'units'
  return (
    <div className="page poetry-page">
      <h1>{m.pat.poetry.title}</h1>
      <div className="toolbar">
        <Segmented
          label={m.pat.view}
          value={view}
          onChange={(v) => update({ view: v === 'units' ? null : v, page: null })}
          options={[
            { value: 'units', label: m.pat.poetry.unitsView },
            { value: 'pairs', label: m.pat.poetry.pairsView },
          ]}
        />
      </div>
      {view === 'pairs' ? <WordPairsView /> : <UnitsView />}
    </div>
  )
}

function UnitsView() {
  const { m, locale } = useLocale()
  const t = m.pat.poetry
  const [params, update] = useQueryParams()
  const raw = params.get('type') as UnitType | null
  const unitType = raw && TYPES.includes(raw) ? raw : 'chapter'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const excludePoetic = params.get('all') !== '1'
  const sort = params.get('sort') === 'antithetic' ? 'antithetic' : 'prob'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { unitType, book, excludePoetic, sort, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE } as const
  const res = useParallelism(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const name = new Map(books.data?.map((b) => [b.book_id, bookName(b, locale)]) ?? [])
  const auc = res.data ? Object.values(res.data.held_out_auc) : []
  const typing = res.data?.typing
  const pctOf = (x: number | null | undefined) => (x == null ? '—' : `${(x * 100).toFixed(1)}%`)

  return (
    <>
      <p className="lede">{t.lede}</p>
      {auc.length > 0 && <p className="muted small">{t.heldOut(auc.map((a) => a.toFixed(2)).join(' · '))}</p>}
      {typing && (
        <p className="muted small">
          {t.typing(
            typing.antithetic,
            typing.synonymous,
            pctOf(typing.check_share),
            pctOf(typing.rest_share),
            pctOf(typing.null_share),
            pctOf(typing.pair_antithetic_share),
          )}
        </p>
      )}

      {res.data && <BookBars books={res.data.books} name={name} onPick={(b) => set({ book: String(b) })} />}

      <div className="toolbar">
        <Segmented
          label={m.units.unitType}
          value={unitType}
          onChange={(v) => set({ type: v === 'chapter' ? null : v })}
          options={TYPES.map((v) => ({ value: v, label: m.units.type(v) }))}
        />
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.search.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        {typing && (
          <Segmented
            label={t.sortBy}
            value={sort}
            onChange={(v) => set({ sort: v === 'prob' ? null : v })}
            options={(['prob', 'antithetic'] as const).map((v) => ({ value: v, label: t.sorts[v] }))}
          />
        )}
        <label className="check" title={t.includePoeticTitle}>
          <input type="checkbox" checked={!excludePoetic} onChange={(e) => set({ all: e.target.checked ? '1' : null })} />
          {t.includePoetic}
        </label>
      </div>

      <PagedList
        res={res}
        empty={t.empty}
        summary={(data) => (
          <>
            {sort === 'antithetic'
            ? t.rankedAnti(data.total, m.units.plural(unitType), data.min_parallel)
            : t.ranked(data.total, m.units.plural(unitType))}{' '}
            · {m.pat.pageOf(page, pages)}
            {' · '}
            <ExportCsv
            all={{ list: 'poetry', params: parallelismParams(query) }}
            filename={`parallel-halves-${unitType}-p${page}.csv`}
            rows={() =>
            data.items.map((r) => ({
            unit: r.unit.label_en,
            share_parallel: r.share_parallel,
            share_antithetic: r.share_antithetic,
            mean_prob: r.mean_prob,
            verses: r.n_scored,
            }))
            }
            />
          </>
        )}
      >
        {(data, stale) => (
          <div className="table-wrap">
            <table className={`change-table ${stale}`}>
              <thead>
                <tr>
                  <th>{m.units.type(unitType)}</th>
                  <th className="num" title={t.parallelTitle}>
                    {t.parallelVerses}
                  </th>
                  {typing && (
                    <th className="num" title={t.antitheticTitle}>
                      {t.antithetic}
                    </th>
                  )}
                  <th className="num" title={t.meanTitle}>
                    {t.mean}
                  </th>
                  <th className="num">{t.verses}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.unit.unit_id}>
                    <td>
                      <Link to={unitLink(r.unit.unit_id, '?halves=1')}>{unitLabel(r.unit, locale)}</Link>
                      {locale === 'en' && (
                        <>
                          {' '}
                          <span className="he-label" dir="rtl" lang="he">
                            {r.unit.label_he}
                          </span>
                        </>
                      )}
                    </td>
                    <td className="num">{pct(r.share_parallel)}</td>
                    {typing && <td className="num">{pct(r.share_antithetic)}</td>}
                    <td className="num">{r.mean_prob.toFixed(2)}</td>
                    <td className="num">{r.n_scored}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PagedList>
    </>
  )
}

function BookBars({ books, name, onPick }: { books: ParallelBook[]; name: Map<number, string>; onPick: (b: number) => void }) {
  const t = useT().pat.poetry
  return (
    <section aria-label={t.perBook}>
      <h2>{t.byBook}</h2>
      <p className="muted small">{t.perBookLede}</p>
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

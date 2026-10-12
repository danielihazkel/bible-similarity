import { Link } from 'react-router'
import { hiddenRootsParams, rootPairsParams, useBooks, useHiddenRoots, useRootPairs, useRoots } from '../api/hooks'
import type { RootPairKind, RootsResponse } from '../api/types'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { lemmaLink, rootLink, unitLink } from '../lib/links'
import { bookName, bookOption, unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20
const KINDS: RootPairKind[] = ['cognate', 'inf_abs', 'other']

/** Root families (§16.38): two words of one root side by side, and key roots of each chapter. */
export function RootsPage() {
  const { m } = useLocale()
  const t = m.root
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'key' ? 'key' : 'pairs'
  const res = useRoots()
  return (
    <div className="page roots-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.meta.tests ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <p className="muted small">{t.families(res.data.meta.families ?? 0, res.data.meta.family_lemmas ?? 0)}</p>
          <div className="toolbar">
            <Segmented
              label={m.pat.view}
              value={view}
              onChange={(v) => update({ view: v === 'pairs' ? null : v, page: null }, false)}
              options={[
                { value: 'pairs', label: t.views.pairs },
                { value: 'key', label: t.views.key },
              ]}
            />
          </div>
          {view === 'key' ? <KeyRoots data={res.data} /> : <Pairs data={res.data} />}
        </>
      )}
    </div>
  )
}

function Pairs({ data }: { data: RootsResponse }) {
  const { m, locale } = useLocale()
  const t = m.root
  const [params, update] = useQueryParams()
  const raw = params.get('kind') as RootPairKind | null
  const kind = raw && KINDS.includes(raw) ? raw : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') ?? undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { kind, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useRootPairs(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const meta = data.meta
  const tests = meta.tests!
  const names = new Map(books.data?.map((b) => [b.book_id, b]) ?? [])
  return (
    <>
      <section aria-label={t.pairsTitle}>
        <h2>{t.pairsTitle}</h2>
        <p className="small">
          {t.cognate(tests.cognate.observed, tests.cognate.expected, tests.cognate.ratio, tests.cognate.p, meta.window ?? 0, meta.shuffles ?? 0)}
        </p>
        <p className="muted small">{t.other(tests.other.observed, tests.other.expected, tests.other.p)}</p>
        <p className="muted small">{t.infAbs(meta.pairs?.inf_abs ?? 0)}</p>
      </section>
      <details className="roots-books">
        <summary>{t.booksTitle}</summary>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.booksTitle}>
          <table className="change-table">
            <thead>
              <tr>
                <th>{t.booksCols.book}</th>
                <th className="num">{t.booksCols.pairs}</th>
                <th className="num">{t.booksCols.expected}</th>
                <th className="num">{t.booksCols.ratio}</th>
                <th className="num">{t.booksCols.per}</th>
                <th className="num">{t.booksCols.inf}</th>
              </tr>
            </thead>
            <tbody>
              {data.books.map((b) => (
                <tr key={b.book_id}>
                  <td>
                    <button type="button" className="linkish" onClick={() => set({ book: String(b.book_id) })}>
                      {names.has(b.book_id) ? bookName(names.get(b.book_id)!, locale) : b.book_id}
                    </button>
                  </td>
                  <td className="num">{b.cognate}</td>
                  <td className="num">{b.expected.toFixed(1)}</td>
                  <td className="num">{b.expected > 0 ? (b.cognate / b.expected).toFixed(1) : '—'}</td>
                  <td className="num">{b.words ? ((1000 * b.cognate) / b.words).toFixed(1) : '—'}</td>
                  <td className="num">{b.inf_abs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{t.kind}</span>
          <select value={kind ?? ''} onChange={(e) => set({ kind: e.target.value || null })}>
            <option value="">{t.anyKind}</option>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {t.kinds[k]}
              </option>
            ))}
          </select>
        </label>
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
      </div>
      <PagedList
        res={res}
        empty={t.noData}
        summary={(d) => (
          <>
            {t.pairsCount(d.total)} · {m.pat.pageOf(page, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'root-pairs', params: rootPairsParams(query) }}
              filename={`root-pairs-p${page}.csv`}
              rows={() => d.items.map((p) => ({ verse: p.label, kind: p.kind, root: p.root_he, first: p.a.he_lemma, second: p.b.he_lemma }))}
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((p) => (
              <li key={p.pair_id} className="hit root-pair">
                <div className="hit-head">
                  <Link className="hit-ref" to={unitLink(`v:${p.verse_id}`)}>
                    <UnitName en={p.label} he={p.label_he} />
                  </Link>{' '}
                  <span className="type-tag">{t.kinds[p.kind]}</span>{' '}
                  {p.kind !== 'inf_abs' ? (
                    <Link to={rootLink(p.root)} className="small">
                      {t.root}{' '}
                      <span dir="rtl" lang="he">
                        {p.root_he}
                      </span>
                    </Link>
                  ) : (
                    <Link to={lemmaLink(p.a.lemma)} className="small" dir="rtl" lang="he">
                      {p.a.he_lemma}
                    </Link>
                  )}
                </div>
                <p className="hit-text">
                  <HebrewText
                    verse={p.verse}
                    highlight={new Map(Object.entries(p.marks).map(([i, side]) => [Number(i), side === 0 ? 'focus' : 'shared'])) as Highlight}
                  />
                </p>
              </li>
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}

function KeyRoots({ data }: { data: RootsResponse }) {
  const { m, locale } = useLocale()
  const t = m.root
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') ?? undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useHiddenRoots(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const meta = data.meta
  const he = (s: string) => (
    <span dir="rtl" lang="he">
      {s}
    </span>
  )
  return (
    <>
      <section aria-label={t.knownTitle}>
        <h2>{t.knownTitle}</h2>
        <p className="small">
          {t.known(meta.known_top_root ?? 0, meta.known_top_lemma ?? 0, data.known.length, meta.top ?? 0, meta.known_better ?? 0)}
        </p>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownTitle}>
          <table className="change-table">
            <thead>
              <tr>
                <th>{t.knownCols.chapter}</th>
                <th>{t.knownCols.root}</th>
                <th className="num">{t.knownCols.byLemma}</th>
                <th className="num">{t.knownCols.byRoot}</th>
              </tr>
            </thead>
            <tbody>
              {data.known.map((k) => (
                <tr key={`${k.unit.unit_id}-${k.root}`}>
                  <td>
                    <Link to={unitLink(k.unit.unit_id, '?structure=1')}>{unitLabel(k.unit, locale)}</Link>
                  </td>
                  <td>
                    <Link to={rootLink(k.root)}>{he(k.root_he)}</Link>
                  </td>
                  <td className="num">{k.lemma_rank ?? '—'}</td>
                  <td className="num">{k.root_rank ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section aria-label={t.hiddenTitle}>
        <h2>{t.hiddenTitle}</h2>
        <p className="muted small">{t.hiddenLede(meta.hidden ?? 0, meta.top ?? 0)}</p>
        {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
        <div className="toolbar">
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
        </div>
        <PagedList
          res={res}
          empty={t.noData}
          summary={(d) => (
            <>
              {m.pat.pageOf(page, pages)}
              {' · '}
              <ExportCsv
                all={{ list: 'hidden-roots', params: hiddenRootsParams(query) }}
                filename={`hidden-roots-p${page}.csv`}
                rows={() => d.items.map((h) => ({ chapter: h.unit.label_en, root: h.root_he, words: h.lemmas.map((l) => l.he_lemma).join(' '), count: h.count, rank: h.rank, best_word: h.lemma_rank }))}
              />
            </>
          )}
        >
          {(d, stale) => (
            <div className="table-wrap">
              <table className={`change-table ${stale}`}>
                <thead>
                  <tr>
                    <th>{t.hiddenCols.chapter}</th>
                    <th>{t.hiddenCols.root}</th>
                    <th>{t.hiddenCols.words}</th>
                    <th className="num">{t.hiddenCols.count}</th>
                    <th className="num">{t.hiddenCols.rank}</th>
                    <th className="num">{t.hiddenCols.lemmaRank}</th>
                  </tr>
                </thead>
                <tbody>
                  {d.items.map((h) => (
                    <tr key={`${h.unit.unit_id}-${h.root}`}>
                      <td>
                        <Link to={unitLink(h.unit.unit_id, '?structure=1')}>{unitLabel(h.unit, locale)}</Link>
                      </td>
                      <td>
                        <Link to={rootLink(h.root)}>{he(h.root_he)}</Link>
                      </td>
                      <td>
                        {h.lemmas.map((l, i) => (
                          <span key={l.lemma}>
                            {i > 0 && ' · '}
                            <Link to={lemmaLink(l.lemma)}>{he(l.he_lemma)}</Link>
                          </span>
                        ))}
                      </td>
                      <td className="num">{h.count}</td>
                      <td className="num">{h.rank}</td>
                      <td className="num">{h.lemma_rank ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </PagedList>
      </section>
    </>
  )
}

import { Link } from 'react-router'
import { useAcrostics, useBooks } from '../api/hooks'
import { AcrosticChain } from '../components/AcrosticChain'
import { ExportCsv } from '../components/ExportCsv'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { granularityLabel, qLabel } from '../lib/format'
import { unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const Q_OPTIONS = [
  { value: '0.05', label: 'q ≤ 0.05 (significant)' },
  { value: '0.5', label: 'q ≤ 0.5 (candidates)' },
  { value: 'all', label: 'Every chapter' },
]
const Q_TITLE = 'Benjamini–Hochberg q over all chapters: the share of chance chains expected among chains this strong'

/** Chapters whose lines run through the alphabet (alphabetic acrostics, whole or broken). */
export function AcrosticsPage() {
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const qRaw = params.get('q') ?? '0.05'
  const qChoice = Q_OPTIONS.some((o) => o.value === qRaw) ? qRaw : '0.05'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useAcrostics({
    maxQ: qChoice === 'all' ? undefined : Number(qChoice),
    book,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const bookName = (id: number) => books.data?.find((b) => b.book_id === id)?.name ?? ''

  return (
    <div className="page acrostics-page">
      <h1>Acrostics</h1>
      <p className="lede">
        Poems whose lines start with the letters of the alphabet in order: verse by verse (Psalm 145, Proverbs 31,
        Lamentations 1), half-verse by half-verse (Psalms 111–112) or in blocks of verses (Psalm 119, Lamentations 3) — and
        broken ones with letters missing or out of place (Psalms 9–10). For every chapter the longest run through the
        alphabet is found, a skipped letter costing one, and compared with the same chapter's lines shuffled.
      </p>
      {res.data?.known_recall != null && (
        <p className="muted small">
          Check: {Math.round(res.data.known_recall * 100)}% of the acrostics scholars list are found with q ≤ 0.05.
        </p>
      )}
      <div className="toolbar">
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
        <label className="control">
          <span>Show</span>
          <select value={qChoice} onChange={(e) => set({ q: e.target.value === '0.05' ? null : e.target.value })}>
            {Q_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No chapters match these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} chapters · page {page} of {pages}
            {' · '}
            <ExportCsv
              filename={`acrostics-p${page}.csv`}
              rows={() =>
                res.data.items.map((a) => ({
                  chapter: a.unit.label_en,
                  letters: a.n_letters,
                  skipped: a.missing,
                  from: a.first_letter,
                  to: a.last_letter,
                  lines: a.granularity,
                  order: a.order_name,
                  p: a.p,
                  q: a.q,
                }))
              }
            />
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((a) => (
              <li key={a.unit.unit_id} className="disc acrostic-card">
                <div className="hit-head">
                  <Link to={unitLink(a.unit.unit_id, '?acrostic=1')}>
                    {a.unit.label_en}{' '}
                    <span className="he-label" dir="rtl" lang="he">
                      {a.unit.label_he}
                    </span>
                  </Link>
                  <span className="phrase-tag">
                    {a.n_letters} letters{a.missing > 0 && `, ${a.missing} skipped`}
                  </span>
                  <span className="muted small">
                    {granularityLabel(a.granularity)}
                    {a.order_name === 'pe-ayin' && ' · פ before ע'}
                  </span>
                  <span className={`small ${a.q <= 0.05 ? 'q-strong' : 'muted'}`} title={Q_TITLE}>
                    {qLabel(a.q)}
                  </span>
                  {!book && <span className="muted small">{bookName(a.unit.book_id)}</span>}
                </div>
                <AcrosticChain a={a} />
              </li>
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}

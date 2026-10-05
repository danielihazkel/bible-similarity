import { useBooks, useSequences } from '../api/hooks'
import type { SequenceDirection } from '../api/types'
import { Pager } from '../components/Pager'
import { ExportCsv } from '../components/ExportCsv'
import { SequenceCard } from '../components/SequenceCard'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
// The default hides chains that a text with shuffled verse order produces about as often.
const ORDERS: { value: SequenceDirection | 'any'; label: string; title: string }[] = [
  { value: 'forward', label: 'Same order', title: 'Both passages advance together' },
  { value: 'reverse', label: 'Mirrored', title: 'One passage runs backwards: A B C … C′ B′ A′' },
  { value: 'mixed', label: 'Reordered', title: 'The same scene told in another order' },
  { value: 'any', label: 'Any order', title: '' },
]
const Q_OPTIONS = [
  { value: '0.05', label: 'q ≤ 0.05 (strong)' },
  { value: '0.2', label: 'q ≤ 0.2' },
  { value: 'all', label: 'All chains' },
]

/** Passages that run parallel verse by verse, in the same order (retellings, synoptic accounts). */
export function SequencesPage() {
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const hideSameChapter = params.get('internal') === '0'
  const qRaw = params.get('q') ?? '0.05'
  const qChoice = Q_OPTIONS.some((o) => o.value === qRaw) ? qRaw : '0.05'
  const unit = params.get('unit') || undefined
  const orderRaw = params.get('order')
  const order = ORDERS.find((o) => o.value === orderRaw)?.value ?? 'forward'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useSequences({
    book,
    crossBook,
    hideSameChapter,
    unit,
    direction: order === 'any' ? undefined : order,
    maxQ: qChoice === 'all' ? undefined : Number(qChoice),
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page sequences-page">
      <h1>Parallel sequences</h1>
      <p className="lede">
        Passages that run alongside each other verse by verse, in the same order: synoptic accounts (Samuel–Kings and
        Chronicles), retold stories, a command and its execution, repeated lists. Each chain links similar verse pairs whose
        positions advance together on both sides; q estimates how often such a chain appears when verse order is shuffled
        within chapters.
      </p>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
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
          <span>Order</span>
          <select value={order} onChange={(e) => set({ order: e.target.value === 'forward' ? null : e.target.value })}>
            {ORDERS.map((o) => (
              <option key={o.value} value={o.value} title={o.title}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>Significance</span>
          <select value={qChoice} onChange={(e) => set({ q: e.target.value === '0.05' ? null : e.target.value })}>
            {Q_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={crossBook} onChange={(e) => set({ cross: e.target.checked ? '1' : null })} />
          Different books only
        </label>
        <label className="check" title="Hide repeats inside one chapter (lists such as Numbers 7)">
          <input
            type="checkbox"
            checked={hideSameChapter}
            onChange={(e) => set({ internal: e.target.checked ? '0' : null })}
          />
          Hide repeats within a chapter
        </label>
      </div>

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">
          No sequences match these filters.
          {order !== 'forward' && qChoice !== 'all' && ' Mirrored and reordered chains never beat the shuffled-order baseline: choose “All chains”.'}
        </p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} sequences · page {page} of {pages}
            {' · '}
            <ExportCsv
              filename={`sequences-p${page}.csv`}
              rows={() =>
                res.data.items.map((s) => ({
                  id: s.seq_id,
                  a: s.a_label,
                  b: s.b_label,
                  verse_pairs: s.n_pairs,
                  score: s.score,
                  q: s.q,
                  sefaria_links: s.n_gold,
                }))
              }
            />
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((s) => (
              <SequenceCard key={s.seq_id} s={s} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}

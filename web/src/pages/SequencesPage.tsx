import { useBooks, useSequences } from '../api/hooks'
import { Pager } from '../components/Pager'
import { SequenceCard } from '../components/SequenceCard'
import { ErrorBox, Loading } from '../components/Status'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
// The default hides chains that a text with shuffled verse order produces about as often.
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
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useSequences({
    book,
    crossBook,
    hideSameChapter,
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
        <p className="status">No sequences match these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} sequences · page {page} of {pages}
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

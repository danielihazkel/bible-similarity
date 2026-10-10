import { useBooks, useSequences, sequencesParams } from '../api/hooks'
import type { SequenceDirection } from '../api/types'
import { PagedList } from '../components/Pager'
import { Segmented } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { SequenceCard } from '../components/SequenceCard'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'
import { SequenceArcs } from './SequenceArcs'

const PAGE_SIZE = 50
// The default hides chains that a text with shuffled verse order produces about as often.
const ORDERS: (SequenceDirection | 'any')[] = ['forward', 'reverse', 'mixed', 'any']
const Q_OPTIONS = ['0.05', '0.2', 'all']

/** Passages that run parallel verse by verse, in the same order (retellings, synoptic accounts); as a
 * list, or (`?view=arcs`) as arcs across the canon. */
export function SequencesPage() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const arcs = params.get('view') === 'arcs'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const hideSameChapter = params.get('internal') === '0'
  const qRaw = params.get('q') ?? '0.05'
  const qChoice = Q_OPTIONS.includes(qRaw) ? qRaw : '0.05'
  const unit = params.get('unit') || undefined
  const orderRaw = params.get('order')
  const order = ORDERS.find((o) => o === orderRaw) ?? 'forward'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = {
    book,
    crossBook,
    hideSameChapter,
    unit,
    direction: order === 'any' ? undefined : order,
    maxQ: qChoice === 'all' ? undefined : Number(qChoice),
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  const res = useSequences(query, !arcs)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page sequences-page">
      <h1>{m.par.sequences.title}</h1>
      <p className="lede">{m.par.sequences.lede}</p>
      <Segmented
        label={m.par.sequences.viewLabel}
        value={arcs ? 'arcs' : 'list'}
        options={[
          { value: 'list', label: m.par.sequences.views.list },
          { value: 'arcs', label: m.par.sequences.views.arcs },
        ]}
        onChange={(v) => set({ view: v === 'arcs' ? 'arcs' : null })}
      />
      {unit && !arcs && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{m.par.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.par.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{m.par.sequences.order}</span>
          <select value={order} onChange={(e) => set({ order: e.target.value === 'forward' ? null : e.target.value })}>
            {ORDERS.map((o) => (
              <option key={o} value={o} title={m.par.sequences.orders[o].hint}>
                {m.par.sequences.orders[o].label}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{m.par.sequences.significance}</span>
          <select value={qChoice} onChange={(e) => set({ q: e.target.value === '0.05' ? null : e.target.value })}>
            {Q_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {m.par.sequences.qOptions[o]}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={crossBook} onChange={(e) => set({ cross: e.target.checked ? '1' : null })} />
          {m.par.differentBooks}
        </label>
        <label className="check" title={m.par.sequences.hideRepeatsTitle}>
          <input
            type="checkbox"
            checked={hideSameChapter}
            onChange={(e) => set({ internal: e.target.checked ? '0' : null })}
          />
          {m.par.sequences.hideRepeats}
        </label>
      </div>

      {arcs ? (
        <SequenceArcs
          maxQ={query.maxQ}
          direction={query.direction}
          book={book}
          crossBook={crossBook}
          hideSameChapter={hideSameChapter}
          books={books.data ?? []}
        />
      ) : (
        <PagedList
          res={res}
          empty={
            <>
              {m.par.sequences.none}
              {order !== 'forward' && qChoice !== 'all' && m.par.sequences.mirroredHint}
            </>
          }
          summary={(data) => (
            <>
              {m.par.sequences.page(data.total, page, pages)}
              {' · '}
              <ExportCsv
                all={{ list: 'sequences', params: sequencesParams(query) }}
                filename={`sequences-p${page}.csv`}
                rows={() =>
                  data.items.map((s) => ({
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
            </>
          )}
        >
          {(data, stale) => (
            <ol className={`disc-list ${stale}`}>
              {data.items.map((s) => (
                <SequenceCard key={s.seq_id} s={s} />
              ))}
            </ol>
          )}
        </PagedList>
      )}
    </div>
  )
}

import { Link } from 'react-router'
import { useBooks, useSequences, sequencesParams } from '../api/hooks'
import type { SequenceDirection } from '../api/types'
import { PagedList } from '../components/Pager'
import { BookSelect, Segmented, SignificanceFilter, Choice } from '../components/Controls'
import { ExportCsv } from '../components/ExportCsv'
import { SequenceCard } from '../components/SequenceCard'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { parsePage, useQueryParams, parseSignificance, significanceChange } from '../lib/urlState'
import { SequenceArcs } from './SequenceArcs'
import '../i18n/pages/parallels'

const PAGE_SIZE = 50
// The default hides chains that a text with shuffled verse order produces about as often.
const ORDERS: (SequenceDirection | 'any')[] = ['forward', 'reverse', 'mixed', 'any']

/** Passages that run parallel verse by verse, in the same order (retellings, synoptic accounts); as a
 * list, or (`?view=arcs`) as arcs across the canon. */
export function SequencesPage() {
  const { m } = useLocale()
  const [params, update] = useQueryParams()
  const arcs = params.get('view') === 'arcs'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const crossBook = params.get('cross') === '1'
  const hideSameChapter = params.get('internal') === '0'
  const sig = parseSignificance(params, '0.2')
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
    maxQ: sig.maxQ,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  const res = useSequences(query, !arcs)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page sequences-page">
      <h1>{m.par.sequences.title}</h1>
      <p className="lede">
        {m.par.sequences.lede} <Link to="/synopses">{m.par.sequences.synopses}</Link>
      </p>
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
        <BookSelect label={m.par.book} all={m.par.allBooks} books={books.data} value={book} onChange={(v) => set({ book: v })} />
        <Choice label={m.par.sequences.order} value={order} options={ORDERS.map((o) => ({ value: o, label: m.par.sequences.orders[o].label, title: m.par.sequences.orders[o].hint }))} onChange={(v) => set({ order: v === 'forward' ? null : v })} />
        <SignificanceFilter value={sig.choice} second="0.2" onChange={(v) => set(significanceChange(v))} />
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
              {order !== 'forward' && sig.choice !== 'all' && m.par.sequences.mirroredHint}
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

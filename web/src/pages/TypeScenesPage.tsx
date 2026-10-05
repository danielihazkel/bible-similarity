import { Link } from 'react-router'
import { useBooks, useTypeScenes } from '../api/hooks'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { qLabel } from '../lib/format'
import { compareLink, unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const Q_TITLE = 'Expected share of chance alignments among those at least this strong (verb order shuffled inside each passage)'

/** Passages whose actions follow the same order: the verbs of two pericopes aligned. */
export function TypeScenesPage() {
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const all = params.get('q') === 'all'
  const showTextual = params.get('textual') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useTypeScenes({
    book,
    maxQ: all ? undefined : 0.05,
    hideTextual: !showTextual,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page typescenes-page">
      <h1>Action sequences</h1>
      <p className="lede">
        Two passages that tell the same actions in the same order, whatever the names and wording: the verbs of every
        pericope are aligned with those of others (rare verbs count more), and each alignment is compared with the same
        passages' verbs shuffled. The strongest are court tales (Daniel 3 and 6: accused, thrown in, rescued), ritual
        procedures and visions retold.
      </p>
      <p className="muted small">
        The classic literary type-scenes (meetings at a well, annunciations to barren women) vary their verbs too much to
        stand out this way: they score little above random pairs of chapters.
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
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => set({ q: e.target.checked ? 'all' : null })} />
          Include q &gt; 0.05
        </label>
        <label className="check" title="Pairs joined by a parallel sequence: the same text told twice">
          <input type="checkbox" checked={showTextual} onChange={(e) => set({ textual: e.target.checked ? '1' : null })} />
          Include textual parallels
        </label>
      </div>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No aligned passages for these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} pairs · page {page} of {pages}
          </p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((t) => (
              <li key={`${t.a.unit_id}|${t.b.unit_id}`} className="disc">
                <div className="hit-head">
                  <Link to={unitLink(t.a.unit_id)}>{t.a.label_en}</Link>
                  <span className="muted">↔</span>
                  <Link to={unitLink(t.b.unit_id)}>{t.b.label_en}</Link>
                  <span className="phrase-tag">{t.n_matches} actions in order</span>
                  <span className={`small ${t.q <= 0.05 ? 'q-strong' : 'muted'}`} title={Q_TITLE}>
                    {qLabel(t.q)}
                  </span>
                  {t.parallel_text && <span className="muted small">textual parallel</span>}
                  <span className="hit-actions">
                    <Link className="linkish" to={compareLink(t.a.unit_id, t.b.unit_id)}>
                      Compare
                    </Link>
                  </span>
                </div>
                <p className="action-chain he" dir="rtl" lang="he">
                  {t.aligned.map((v, i) => (
                    <span key={i} title={`${v.a_vid} ↔ ${v.b_vid}`}>
                      {i > 0 && <span className="muted"> ← </span>}
                      {v.he_lemma}
                    </span>
                  ))}
                </p>
              </li>
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </div>
  )
}

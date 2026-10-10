import { Link } from 'react-router'
import { useBooks, useTypeScenes } from '../api/hooks'
import { PagedList } from '../components/Pager'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { compareLink, unitLink } from '../lib/links'
import { bookOption, unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** Passages whose actions follow the same order: the verbs of two pericopes aligned. */
export function TypeScenesPage() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const all = params.get('q') === 'all'
  const showTextual = params.get('textual') === '1'
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useTypeScenes({
    book,
    maxQ: all ? undefined : 0.05,
    hideTextual: !showTextual,
    unit,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <div className="page typescenes-page">
      <h1>{m.par.typeScenes.title}</h1>
      <p className="lede">{m.par.typeScenes.lede}</p>
      <p className="muted small">{m.par.typeScenes.note}</p>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
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
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => set({ q: e.target.checked ? 'all' : null })} />
          {m.par.includeQ}
        </label>
        <label className="check" title={m.par.typeScenes.textualTitle}>
          <input type="checkbox" checked={showTextual} onChange={(e) => set({ textual: e.target.checked ? '1' : null })} />
          {m.par.typeScenes.textual}
        </label>
      </div>
      <PagedList
        res={res}
        empty={m.par.typeScenes.none}
        summary={(data) => m.par.pairsPage(data.total, page, pages)}
      >
        {(data, stale) => (
          <ol className={`disc-list ${stale}`}>
            {data.items.map((t) => (
              <li key={`${t.a.unit_id}|${t.b.unit_id}`} className="disc">
                <div className="hit-head">
                  <Link to={unitLink(t.a.unit_id)}>{unitLabel(t.a, locale)}</Link>
                  <span className="muted">↔</span>
                  <Link to={unitLink(t.b.unit_id)}>{unitLabel(t.b, locale)}</Link>
                  <span className="phrase-tag">{m.par.typeScenes.actions(t.n_matches)}</span>
                  <span className={`small ${t.q <= 0.05 ? 'q-strong' : 'muted'}`} title={m.par.typeScenes.qTitle}>
                    {m.q(t.q)}
                  </span>
                  {t.parallel_text && <span className="muted small">{m.par.typeScenes.textualTag}</span>}
                  <span className="hit-actions">
                    <Link className="linkish" to={compareLink(t.a.unit_id, t.b.unit_id)}>
                      {m.hit.compare}
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
        )}
      </PagedList>
    </div>
  )
}

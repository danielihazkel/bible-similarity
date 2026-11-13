import { Link } from 'react-router'
import { BookSelect, SignificanceFilter } from '../components/Controls'
import { useBooks, useTypeScenes } from '../api/hooks'
import { PagedList } from '../components/Pager'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { compareLink, lemmaLink, unitLink } from '../lib/links'
import { unitLabel } from '../lib/names'
import { parsePage, useQueryParams, parseSignificance, significanceChange } from '../lib/urlState'
import '../i18n/pages/parallels'
import { PrecisionNote } from '../components/PrecisionNote'
import '../styles/pages/TypeScenesPage.css'

const PAGE_SIZE = 50

/** Passages whose actions follow the same order: the verbs of two pericopes aligned. */
export function TypeScenesPage() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const sig = parseSignificance(params)
  const showTextual = params.get('textual') === '1'
  const unit = params.get('unit') || undefined
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useTypeScenes({
    book,
    maxQ: sig.maxQ,
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
      <PrecisionNote detector="typescenes" />
      <p className="muted small">{m.par.typeScenes.note}</p>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <BookSelect label={m.par.book} all={m.par.allBooks} books={books.data} value={book} onChange={(v) => set({ book: v })} />
        <SignificanceFilter value={sig.choice} onChange={(v) => set(significanceChange(v))} />
        <label className="check" title={m.par.typeScenes.textualTitle}>
          <input type="checkbox" checked={showTextual} onChange={(e) => set({ textual: e.target.checked ? '1' : null })} />
          {m.par.typeScenes.textual}
        </label>
      </div>
      <PagedList
        csv="typescenes"
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
                    <span key={i}>
                      {i > 0 && <span className="muted"> ← </span>}
                      <Link to={lemmaLink(v.lemma)}>{v.he_lemma}</Link>
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

import { Link } from 'react-router'
import { useAllusions, useBooks } from '../api/hooks'
import type { Allusion, Verse } from '../api/types'
import { HebrewText } from '../components/HebrewText'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { hebrewNumeral } from '../lib/hebrew'
import type { Highlight } from '../lib/highlight'
import { compareLink, unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20

/** Passages sharing rare words over a few verses, against a within-chapter shuffle (§16.32). */
export function SpreadView() {
  const { m, locale } = useLocale()
  const t = m.par.spread
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') || undefined
  // new pairs only by default (a unit shows everything that touches it)
  const onlyNew = params.get('all') !== '1' && !unit
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const res = useAllusions({ known: onlyNew ? false : undefined, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const meta = res.data.meta
  if (meta.pairs === undefined) return <p className="status">{t.noData}</p>
  return (
    <>
      <p className="lede">{t.lede(meta.window ?? 3)}</p>
      <p className="small">
        {t.finding(meta.pairs, meta.known ?? 0, meta.strong ?? 0, meta.strong_known ?? 0, meta.best_new_q == null ? '–' : meta.best_new_q.toFixed(2))}
      </p>
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
        {!unit && (
          <label className="check">
            <input type="checkbox" checked={onlyNew} onChange={(e) => set({ all: e.target.checked ? null : '1' })} />
            {t.onlyNew}
          </label>
        )}
      </div>
      {res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>
          {t.none}
        </EmptyList>
      ) : (
        <>
          <p className="muted small">{t.page(res.data.total, page, pages)}</p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((a) => (
              <SpreadItem key={a.allusion_id} a={a} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </>
  )
}

function SpreadItem({ a }: { a: Allusion }) {
  const { m, locale } = useLocale()
  const t = m.par.spread
  return (
    <li className="disc spread-item">
      <div className="hit-head">
        <Link to={unitLink(`v:${a.a_start}`)}>{locale === 'he' ? a.a_label_he : a.a_label}</Link>
        <span className="muted">↔</span>
        <Link to={unitLink(`v:${a.b_start}`)}>{locale === 'he' ? a.b_label_he : a.b_label}</Link>
        <span className="phrase-tag">{t.shared(a.n_shared)}</span>
        <span className={`small ${a.q <= 0.05 ? 'q-strong' : 'muted'}`}>{m.q(a.q)}</span>
        {a.known && <span className="muted small">{t.known}</span>}
        <span className="hit-actions">
          <Link className="linkish" to={compareLink(`v:${a.a_start}`, `v:${a.b_start}`)}>
            {m.hit.compare}
          </Link>
        </span>
      </div>
      <p className="he spread-lemmas" dir="rtl" lang="he">
        {a.lemmas.map((l) => l.form).join(' · ')}
      </p>
      <div className="spread-sides">
        <Side verses={a.a_verses} marks={a.a_marks} />
        <Side verses={a.b_verses} marks={a.b_marks} />
      </div>
    </li>
  )
}

function Side({ verses, marks }: { verses: Verse[]; marks: Record<string, number[]> }) {
  const { locale } = useLocale()
  return (
    <div className="spread-side">
      {verses.map((v) => (
        <p key={v.verse_id}>
          <span className="muted small">{locale === 'he' ? hebrewNumeral(v.verse) : v.verse} </span>
          <HebrewText verse={v} highlight={new Map((marks[v.verse_id] ?? []).map((i) => [i, 'shared'])) as Highlight} />
        </p>
      ))}
    </div>
  )
}

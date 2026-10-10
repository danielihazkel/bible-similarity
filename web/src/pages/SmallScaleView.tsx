import { Link } from 'react-router'
import { useBooks, useMirrorClauses, useMirrors, useMirrorVerses } from '../api/hooks'
import type { MirrorClause, MirrorsMeta, MirrorVerse } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import type { Highlight, Mark } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20
const MARKS: Mark[] = ['focus', 'shared', 'acrostic']

const highlight = (marks: Record<string, number>): Highlight =>
  new Map(Object.entries(marks).map(([i, d]) => [Number(i), MARKS[d % MARKS.length]]))

/** Chiasm at the small scale: repeated words in a verse and the parts of a clause pair (§16.33). */
export function SmallScaleView() {
  const t = useLocale().m.mir
  const res = useMirrors()
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const meta = res.data.meta
  if (!meta.words) return <p className="status">{t.noData}</p>
  return (
    <>
      <p className="lede">{t.lede}</p>
      <Tests meta={meta} />
      <Lists meta={meta} />
    </>
  )
}

function Tests({ meta }: { meta: MirrorsMeta }) {
  const t = useLocale().m.mir
  const w = meta.words!
  const c = meta.clauses
  return (
    <>
      <section aria-label={t.wordsTitle}>
        <h2>{t.wordsTitle}</h2>
        <p className="small">
          {t.words(w.all.verses_chiastic, w.all.verses_parallel, w.all.share, t.range(w.all.interval), t.fp(w.all.p))}{' '}
          {t.wordsGenre(w.poetry.share, w.poetry.verses, w.prose.share, w.prose.verses)}
        </p>
        <p className="muted small">{t.wordsNote}</p>
      </section>
      {c && c.poetry != null && c.prose != null && (
        <section aria-label={t.clausesTitle}>
          <h2>{t.clausesTitle}</h2>
          <p className="small">{t.clauses(c.poetry, c.poetry_n, c.prose, c.prose_n, t.fp(c.p))}</p>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={t.clausesTitle}>
            <table className="change-table">
              <thead>
                <tr>
                  <th>{t.cols.pair}</th>
                  <th className="num">{t.cols.n}</th>
                  <th className="num">{t.cols.poetry}</th>
                  <th className="num">{t.cols.prose}</th>
                </tr>
              </thead>
              <tbody>
                {c.by_pair.map((r) => (
                  <tr key={r.pair}>
                    <td>
                      <Link to={`?view=small&list=clauses&pair=${r.pair}&mirrored=1#mirror-lists`}>{t.pairName(r.pair)}</Link>
                    </td>
                    <td className="num">{r.n.toLocaleString()}</td>
                    <td className="num">{r.poetry == null ? '–' : `${Math.round(r.poetry * 100)}% (${r.poetry_n})`}</td>
                    <td className="num">{r.prose == null ? '–' : `${Math.round(r.prose * 100)}% (${r.prose_n})`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  )
}

function Lists({ meta }: { meta: MirrorsMeta }) {
  const { m, locale } = useLocale()
  const t = m.mir
  const [params, update] = useQueryParams()
  const list = params.get('list') === 'verses' ? 'verses' : 'clauses'
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') || undefined
  const books = useBooks()
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.listsTitle} id="mirror-lists">
      <h2>{t.listsTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented
          label={t.listsTitle}
          value={list}
          options={[
            { value: 'clauses', label: t.lists.clauses },
            { value: 'verses', label: t.lists.verses },
          ]}
          onChange={(v) => set({ list: v === 'verses' ? 'verses' : null })}
        />
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
      </div>
      {list === 'verses' ? (
        <VerseList book={book} unit={unit} k={meta.min_words ?? 3} total={meta.full_mirrors ?? 0} />
      ) : (
        <ClauseList book={book} unit={unit} pairs={meta.clauses?.by_pair.map((r) => r.pair) ?? []} />
      )}
    </section>
  )
}

function ClauseList({ book, unit, pairs }: { book?: number; unit?: string; pairs: string[] }) {
  const t = useLocale().m.mir
  const [params, update] = useQueryParams()
  const pair = pairs.includes(params.get('pair') ?? '') ? (params.get('pair') as string) : undefined
  const mirrored = params.get('mirrored') === '1' ? true : undefined
  const g = params.get('genre')
  const poetic = g === 'poetry' ? true : g === 'prose' ? false : undefined
  const page = parsePage(params.get('page'))
  const res = useMirrorClauses({ pair, mirrored, poetic, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <>
      <div className="toolbar">
        <label className="control">
          <span>{t.filters.pair}</span>
          <select value={pair ?? ''} onChange={(e) => set({ pair: e.target.value || null })}>
            <option value="">{t.filters.any}</option>
            {pairs.map((p) => (
              <option key={p} value={p}>
                {t.pairName(p)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{t.filters.genre}</span>
          <select value={g ?? ''} onChange={(e) => set({ genre: e.target.value || null })}>
            <option value="">{t.filters.any}</option>
            <option value="poetry">{t.filters.poetry}</option>
            <option value="prose">{t.filters.prose}</option>
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={mirrored === true} onChange={(e) => set({ mirrored: e.target.checked ? '1' : null })} />
          {t.filters.mirrored}
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.none}
        summary={(data) => t.page(data.total, page, pages)}
      >
        {(data, stale) => (
          <ol className={`disc-list ${stale}`}>
            {data.items.map((c) => (
              <ClauseItem key={c.pair_id} c={c} />
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}

function ClauseItem({ c }: { c: MirrorClause }) {
  const { m, locale } = useLocale()
  const t = m.mir
  return (
    <li className="disc mirror-item">
      <div className="hit-head">
        <Link to={unitLink(`v:${c.verse_id}`)}>{locale === 'he' ? c.label_he : c.label}</Link>
        <span className="phrase-tag">{t.order(c.first, c.second, c.mirrored)}</span>
        <span className={`small ${c.mirrored ? 'q-strong' : 'muted'}`}>{c.mirrored ? t.mirroredTag : t.parallelTag}</span>
        {c.poetic && <span className="muted small">{t.poetryTag}</span>}
      </div>
      <HebrewText verse={c.verse} highlight={highlight(c.marks)} />
    </li>
  )
}

function VerseList({ book, unit, k, total }: { book?: number; unit?: string; k: number; total: number }) {
  const t = useLocale().m.mir
  const [params] = useQueryParams()
  const page = parsePage(params.get('page'))
  const res = useMirrorVerses({ book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  return (
    <>
      <p className="muted small">{t.fullNote(total, k)}</p>
      <PagedList
        res={res}
        empty={t.none}
        summary={(data) => t.page(data.total, page, pages)}
      >
        {(data, stale) => (
          <ol className={`disc-list ${stale}`}>
            {data.items.map((v) => (
              <VerseItem key={v.verse_id} v={v} />
            ))}
          </ol>
        )}
      </PagedList>
    </>
  )
}

function VerseItem({ v }: { v: MirrorVerse }) {
  const { m, locale } = useLocale()
  const t = m.mir
  return (
    <li className="disc mirror-item">
      <div className="hit-head">
        <Link to={unitLink(`v:${v.verse_id}`)}>{locale === 'he' ? v.label_he : v.label}</Link>
        <span className="phrase-tag">{t.nest(v.n_pairs, v.n_words)}</span>
        <span className="muted small">{t.pq(v.p, v.q)}</span>
        {v.poetic && <span className="muted small">{t.poetryTag}</span>}
      </div>
      <HebrewText verse={v.verse} highlight={highlight(v.marks)} />
    </li>
  )
}

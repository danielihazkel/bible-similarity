import { Link } from 'react-router'
import { useBooks, useSegmentCurve, useSegmentGaps, useSegments } from '../api/hooks'
import type { SegmentGap, SegmentKind, SegmentPoint, SegmentsMeta } from '../api/types'
import { Segmented } from '../components/Controls'
import { HebrewText } from '../components/HebrewText'
import { EmptyList, Pager } from '../components/Pager'
import { ErrorBox, Loading, PanelError } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { useLocale } from '../context/localeContext'
import { hebrewNumeral } from '../lib/hebrew'
import { unitLink } from '../lib/links'
import { bookName, bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 25
const KINDS: SegmentKind[] = ['turn', 'cut', 'quiet']
const GROUPS = [
  'mam_pe',
  'mam_samekh',
  'oshb_pe',
  'oshb_samekh',
  'agreed',
  'single',
  'chapter_break',
  'chapter_only',
  'parasha',
  'seam',
  'unmarked',
]
const f2 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2))
const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

/** Where the text turns, and whether the tradition's divisions fall there (DESIGN.md §16.29). */
export function DivisionsPage() {
  const { m, locale } = useLocale()
  const t = m.div
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const books = useBooks()
  const res = useSegments()
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const { meta } = res.data
  const bookObj = books.data?.find((b) => b.book_id === book)
  return (
    <div className="page divisions-page">
      <h1>{t.title}</h1>
      {meta.window === undefined ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <p className="lede">{t.lede(meta.window)}</p>
          <Tests meta={meta} />
          <section aria-label={t.bookTitle}>
            <h2>{t.bookTitle}</h2>
            <div className="toolbar">
              <label className="control">
                <span>{t.book}</span>
                <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null, ch: null })}>
                  <option value="">{m.par.allBooks}</option>
                  {books.data?.map((b) => (
                    <option key={b.book_id} value={b.book_id}>
                      {bookOption(b, locale)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {book === undefined ? (
              <p className="muted small">{t.pickBook}</p>
            ) : (
              <BookCurve bookId={book} name={bookObj ? bookName(bookObj, locale) : String(book)} />
            )}
          </section>
          <GapList book={book} />
        </>
      )}
    </div>
  )
}

function Tests({ meta }: { meta: SegmentsMeta }) {
  const { m } = useLocale()
  const t = m.div
  const groups = meta.groups ?? {}
  const c = meta.contrasts ?? {}
  const grid = Object.entries(meta.window_grid ?? {})
    .map(([w, s]) => `${w}: ${s.toFixed(3)}`)
    .join(', ')
  return (
    <section aria-label={t.tests}>
      <h2>{t.tests}</h2>
      <p className="muted small">{t.testsLede}</p>
      <div className="table-wrap" tabIndex={0} role="region" aria-label={t.tests}>
        <table className="change-table division-table">
          <thead>
            <tr>
              <th>{t.cols.kind}</th>
              <th className="num">{t.cols.n}</th>
              <th className="num">{t.cols.score}</th>
              <th className="num">{t.cols.lex}</th>
              <th className="num">{t.cols.sem}</th>
              <th className="num">{t.cols.p}</th>
            </tr>
          </thead>
          <tbody>
            {GROUPS.filter((g) => groups[g]).map((g) => (
              <tr key={g}>
                <td>{t.groups[g]}</td>
                <td className="num">{groups[g].n?.toLocaleString() ?? '–'}</td>
                <td className="num">
                  <strong>{f2(groups[g].score)}</strong>
                </td>
                <td className="num">{f2(groups[g].lex)}</td>
                <td className="num">{f2(groups[g].sem)}</td>
                <td className="num">{fp(groups[g].p)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="division-findings small">
        {c.pe_samekh && <li>{t.peSamekh(f2(c.pe_samekh.a), f2(c.pe_samekh.b), fp(c.pe_samekh.p))}</li>}
        {c.agreed_single && <li>{t.agreedSingle(f2(c.agreed_single.a), f2(c.agreed_single.b), fp(c.agreed_single.p))}</li>}
        {c.chapter && <li>{t.chapter(f2(c.chapter.a), f2(c.chapter.b), fp(c.chapter.p))}</li>}
        {meta.seams && meta.seams.share != null && meta.seams.null != null && meta.seams.near != null && (
          <li>{t.seams(meta.seams.share, meta.seams.null, meta.seams.near, fp(meta.seams.p))}</li>
        )}
        {(['mam', 'chapter'] as const).map((ref) => {
          const a = meta.agreement?.[ref]
          return a ? <li key={ref}>{t.agreement(ref, a.better, a.books, f2(a.pk), f2(a.pk_null))}</li> : null
        })}
      </ul>
      <p className="muted small">
        {meta.calibration && `${t.calibration(f2(meta.calibration.score), fp(meta.calibration.p))} `}
        {meta.window !== undefined && t.window(meta.window, grid)}
      </p>
      <p className="muted small">{t.caveat}</p>
    </section>
  )
}

function BookCurve({ bookId, name }: { bookId: number; name: string }) {
  const { m, locale } = useLocale()
  const t = m.div
  const [params, update] = useQueryParams()
  const res = useSegmentCurve(bookId)
  if (res.isPending) return <Loading />
  if (res.error) return <PanelError what={t.bookTitle} error={res.error} />
  const { points, agreement } = res.data
  if (points.length === 0) return <p className="status">{t.none}</p>
  const chapters = [...new Set(points.map((p) => p.chapter))]
  const chParam = Number(params.get('ch'))
  const ch = chapters.includes(chParam) ? chParam : undefined
  // a gap belongs to the verse after it, so a chapter's view opens with the boundary before it
  const shown = ch === undefined ? points : points.filter((p) => p.chapter === ch)
  return (
    <>
      <div className="toolbar">
        <label className="control">
          <span>{t.chapter_}</span>
          <select value={ch ?? ''} onChange={(e) => update({ ch: e.target.value || null })}>
            <option value="">{t.allChapters}</option>
            {chapters.map((c) => (
              <option key={c} value={c}>
                {locale === 'he' ? hebrewNumeral(c) : c}
              </option>
            ))}
          </select>
        </label>
      </div>
      <DivisionChart points={shown} label={t.chart(name)} />
      <p className="division-legend small" aria-hidden="true">
        <span className="swatch div-pe" /> {t.legend.pe} <span className="swatch div-samekh" /> {t.legend.samekh}{' '}
        <span className="swatch div-none" /> {t.legend.other} <span className="swatch div-chapter" /> {t.legend.chapter}
      </p>
      <ul className="small">
        {agreement.map((a) => (
          <li key={a.ref}>{t.bookAgreement(a.ref, f2(a.pk), f2(a.pk_null), fp(a.pk_p))}</li>
        ))}
      </ul>
    </>
  )
}

function DivisionChart({ points, label }: { points: SegmentPoint[]; label: string }) {
  const { m } = useLocale()
  const t = m.div
  const W = 760
  const H = 170
  const pad = { l: 30, r: 8, t: 10, b: 24 }
  const n = points.length
  const x = (i: number) => pad.l + ((i + 0.5) / n) * (W - pad.l - pad.r)
  const y = (s: number) => pad.t + (1 - s) * (H - pad.t - pad.b)
  const bar = Math.max(1, Math.min(10, ((W - pad.l - pad.r) / n) * 0.7))
  const starts = points.map((p, i) => [p, i] as const).filter(([p]) => p.chapter_start)
  const every = Math.max(1, Math.ceil(starts.length / 14))
  return (
    <svg className="division-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} direction="ltr">
      {[0, 0.5, 1].map((s) => (
        <g key={s}>
          <line x1={pad.l} x2={W - pad.r} y1={y(s)} y2={y(s)} className="chart-grid" />
          <text x={4} y={y(s) + 3} className="axis">
            {s}
          </text>
        </g>
      ))}
      {starts.map(([p, i], j) => (
        <g key={`c${p.verse_id}`}>
          <line x1={x(i)} x2={x(i)} y1={pad.t} y2={H - pad.b} className="div-chapter-line" />
          {j % every === 0 && (
            <text x={x(i)} y={H - 8} textAnchor="middle" className="axis">
              {p.chapter}
            </text>
          )}
        </g>
      ))}
      {points.map((p, i) => (
        <line
          key={p.verse_id}
          x1={x(i)}
          x2={x(i)}
          y1={y(0)}
          y2={y(p.score)}
          strokeWidth={bar}
          className={p.mam === 'pe' ? 'div-pe' : p.mam === 'samekh' ? 'div-samekh' : 'div-none'}
        >
          <title>{t.bar(m.cv(p.chapter, p.verse), p.score.toFixed(2))}</title>
        </line>
      ))}
    </svg>
  )
}

function GapList({ book }: { book?: number }) {
  const { m } = useLocale()
  const t = m.div
  const [params, update] = useQueryParams()
  const kindParam = params.get('kind')
  const unit = params.get('unit') || undefined
  // a unit's points come in reading order and of every kind; otherwise one list at a time
  const kind: SegmentKind | undefined = KINDS.includes(kindParam as SegmentKind)
    ? (kindParam as SegmentKind)
    : unit
      ? undefined
      : 'turn'
  const page = parsePage(params.get('page'))
  const res = useSegmentGaps({ kind, book, unit, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.listTitle}>
      <h2>{t.listTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <Segmented<string>
          label={t.listTitle}
          value={kind ?? ''}
          options={[
            ...(unit ? [{ value: '', label: t.anyKind }] : []),
            ...KINDS.map((k) => ({ value: k, label: t.kinds[k].label, title: t.kinds[k].hint })),
          ]}
          onChange={(v) => set({ kind: v || null })}
        />
      </div>
      {kind && <p className="muted small">{t.kinds[kind].hint}</p>}
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <EmptyList total={res.data.total} limit={res.data.limit}>
          {t.none}
        </EmptyList>
      ) : (
        <>
          <p className="muted small">{t.page(res.data.total, page, pages)}</p>
          <ol className={`disc-list ${res.isPlaceholderData ? 'stale' : ''}`}>
            {res.data.items.map((g) => (
              <GapItem key={g.verse_id} g={g} showKind={kind === undefined} />
            ))}
          </ol>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </section>
  )
}

function GapItem({ g, showKind }: { g: SegmentGap; showKind: boolean }) {
  const { m, locale } = useLocale()
  const t = m.div
  const books = useBooks()
  const b = books.data?.find((x) => x.book_id === g.book_id)
  const [before, after] = g.verses
  return (
    <li className="disc gap-item">
      <div className="hit-head">
        <Link to={unitLink(`v:${g.verse_id}`)}>{locale === 'he' ? g.label_he : g.label}</Link>
        {b && <span className="muted small">{bookName(b, locale)}</span>}
        <span className="phrase-tag" title={t.scoreTitle}>
          {t.score(g.score.toFixed(2))}
        </span>
        {showKind && g.kind && <span className="small">{t.kinds[g.kind].label}</span>}
        {g.mam && <span className="muted small">{t.tags.mam(g.mam)}</span>}
        {g.oshb && <span className="muted small">{t.tags.oshb(g.oshb)}</span>}
        {g.chapter && <span className="muted small">{t.tags.chapter}</span>}
        {g.seam && <span className="muted small">{t.tags.seam}</span>}
      </div>
      <div className="gap-verses">
        {before && <HebrewText verse={before} className="gap-before" />}
        <span className="gap-mark" role="separator" aria-label={t.boundary} />
        {after && <HebrewText verse={after} />}
      </div>
    </li>
  )
}

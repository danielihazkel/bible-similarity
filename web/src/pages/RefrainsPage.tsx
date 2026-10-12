import { Link } from 'react-router'
import { refrainParams, useBooks, useRefrainList, useRefrains } from '../api/hooks'
import type { Refrain, RefrainsResponse } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { UnitFilter } from '../components/UnitFilter'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import type { Highlight } from '../lib/highlight'
import { readLink, unitLink } from '../lib/links'
import { bookOption } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20

/** Refrains (§16.40): phrases that come back inside a passage, the checks, and the list. */
export function RefrainsPage() {
  const { m } = useLocale()
  const t = m.ref
  const res = useRefrains()
  const meta = res.data?.meta
  return (
    <div className="page refrains-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede(meta?.min_tokens ?? 3, meta?.min_count ?? 3, meta?.max_gap ?? 20)}</p>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : !res.data.meta.detect ? (
        <p className="status">{t.noData}</p>
      ) : (
        <>
          <Tests data={res.data} />
          <List alpha={res.data.meta.alpha ?? 0.05} />
        </>
      )}
    </div>
  )
}

function Tests({ data }: { data: RefrainsResponse }) {
  const { m, locale } = useLocale()
  const t = m.ref
  const meta = data.meta
  const d = meta.detect!
  const g = meta.regular
  const turns = meta.turns
  return (
    <>
      <p className="small">{t.detect(d.observed ?? 0, d.expected ?? 0, meta.shuffles ?? 0, meta.distinct ?? 0)}</p>
      <section aria-label={t.knownTitle}>
        <h2>{t.knownTitle}</h2>
        <p className="small">{t.knownLede(meta.known_found ?? 0, data.known.length)}</p>
        <div className="table-wrap" tabIndex={0} role="region" aria-label={t.knownTitle}>
          <table className="change-table">
            <thead>
              <tr>
                <th>{t.knownCols.name}</th>
                <th>{t.knownCols.where}</th>
                <th>{t.knownCols.found}</th>
                <th className="num">{t.knownCols.k}</th>
                <th className="num">{t.knownCols.q}</th>
              </tr>
            </thead>
            <tbody>
              {data.known.map((k) => (
                <tr key={k.name}>
                  <td dir="rtl" lang="he" className="he-cell">
                    {k.name}
                  </td>
                  <td>
                    <Link to={readLink(`v:${k.first_vid}`, '?layers=refrains')}>{locale === 'he' ? k.label_he : k.label}</Link>
                  </td>
                  <td>
                    {k.text ? (
                      <span dir="rtl" lang="he" className="he-cell">
                        {k.text}
                      </span>
                    ) : (
                      <span className="muted">{t.notFound}</span>
                    )}
                  </td>
                  <td className="num">{k.k ?? '–'}</td>
                  <td className="num">{k.q == null ? '–' : t.qValue(k.q)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {g && g.testable > 0 && (
        <section aria-label={t.regularTitle}>
          <h2>{t.regularTitle}</h2>
          <p className="small">{t.regular(g.regular, g.testable, g.share, g.p)}</p>
        </section>
      )}
      {turns && turns.p != null && (
        <section aria-label={t.turnsTitle}>
          <h2>{t.turnsTitle}</h2>
          <p className="small">{t.turns(turns.observed, turns.expected, turns.p ?? null, turns.n ?? 0)}</p>
        </section>
      )}
    </>
  )
}

function List({ alpha }: { alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.ref
  const [params, update] = useQueryParams()
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const unit = params.get('unit') ?? undefined
  const strongest = params.get('all') !== '1'
  const known = params.get('known') === '1'
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { book, unit, strongest, known, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useRefrainList(query)
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  return (
    <section aria-label={t.listTitle}>
      <h2>{t.listTitle}</h2>
      {unit && <UnitFilter unitId={unit} onClear={() => set({ unit: null })} />}
      <div className="toolbar">
        <label className="control">
          <span>{m.search.book}</span>
          <select value={book ?? ''} onChange={(e) => set({ book: e.target.value || null })}>
            <option value="">{m.search.allBooks}</option>
            {books.data?.map((b) => (
              <option key={b.book_id} value={b.book_id}>
                {bookOption(b, locale)}
              </option>
            ))}
          </select>
        </label>
        <label className="check" title={t.strongestTitle}>
          <input type="checkbox" checked={strongest} onChange={(e) => set({ all: e.target.checked ? null : '1' })} />
          {t.strongestOnly}
        </label>
        <label className="check">
          <input type="checkbox" checked={known} onChange={(e) => set({ known: e.target.checked ? '1' : null })} />
          {t.knownOnly}
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.empty}
        summary={(d, p, pages) => (
          <>
            {t.count(d.total)} · {m.pat.pageOf(p, pages)}
            {' · '}
            <ExportCsv
              all={{ list: 'refrains', params: refrainParams(query) }}
              filename={`refrains-p${p}.csv`}
              rows={() =>
                d.items.map((r) => ({ refrain: r.text, verses: r.k, first: r.occurrences[0]?.label ?? '', q: r.q, known: r.known ?? '' }))
              }
            />
          </>
        )}
      >
        {(d, stale) => (
          <ol className={`hits ${stale}`}>
            {d.items.map((r) => (
              <RefrainItem key={r.refrain_id} r={r} alpha={alpha} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function RefrainItem({ r, alpha }: { r: Refrain; alpha: number }) {
  const { m, locale } = useLocale()
  const t = m.ref
  const label = (o: Refrain['occurrences'][number]) => (locale === 'he' ? o.label_he : o.label)
  const first = r.occurrences[0]
  const last = r.occurrences[r.occurrences.length - 1]
  const marks = new Map(r.occurrences.map((o) => [o.verse_id, o]))
  return (
    <li className="hit refrain">
      <div className="hit-head">
        <span className="refrain-text he" dir="rtl" lang="he">
          {r.text}
        </span>{' '}
        <span className="type-tag">{t.verses(r.k)}</span>{' '}
        <span className="muted small">
          {first && last && t.span(label(first), label(last))} · {t.q(r.q)}
          {r.regular_p != null && <> · {r.regular_p <= alpha ? t.even(r.regular_p) : t.uneven}</>}
          {r.turn != null && (
            <>
              {' · '}
              <span title={t.turnTitle}>{t.turn(r.turn)}</span>
            </>
          )}
          {r.known && (
            <>
              {' · '}
              {t.named}
              <span dir="rtl" lang="he">
                {r.known}
              </span>
            </>
          )}
        </span>{' '}
        {first && (
          <Link className="small" to={readLink(`v:${first.verse_id}`, '?layers=refrains')} title={t.readTitle}>
            {t.read}
          </Link>
        )}
      </div>
      {r.verses.map((v) => {
        const o = marks.get(v.verse_id)
        const hl: Highlight = new Map()
        if (o) for (let i = o.first; i <= o.last; i++) hl.set(i, 'shared')
        return (
          <p key={v.verse_id} className="hit-text">
            <Link className="verse-ref small" to={unitLink(`v:${v.verse_id}`)}>
              <UnitName en={o?.label ?? v.ref} he={o?.label_he ?? v.ref_he} />
            </Link>{' '}
            <HebrewText verse={v} highlight={hl} />
          </p>
        )
      })}
      {r.occurrences.length > r.verses.length && (
        <p className="muted small refrain-more">
          {t.more(r.occurrences.length - r.verses.length)}:{' '}
          {r.occurrences.slice(r.verses.length).map((o, i) => (
            <span key={o.verse_id}>
              {i > 0 && ', '}
              <Link to={unitLink(`v:${o.verse_id}`)}>{label(o)}</Link>
            </span>
          ))}
        </p>
      )}
    </li>
  )
}

import { Link } from 'react-router'
import { meterParams, useBooks, useMeter } from '../api/hooks'
import type { MeterChapter, MeterGroup, MeterResponse } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { useLocale } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { bookOption, unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const GROUPS: MeterGroup[] = ['test', 'control', 'pool', 'poetic', 'prose']
const pct = (x: number | null) => (x === null ? '—' : `${Math.round(x * 100)}%`)
const x2 = (x: number | null | undefined) => (x == null ? '—' : x.toFixed(2))
const fp = (p: number | null | undefined) => (p == null ? '—' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

/** Stresses per line and the falling lament line (§16.37): the tests, then chapters by net fall. */
export function MeterView() {
  const { m, locale } = useLocale()
  const t = m.met
  const [params, update] = useQueryParams()
  const raw = params.get('group') as MeterGroup | null
  const group = raw && GROUPS.includes(raw) ? raw : undefined
  const bookParam = params.get('book')
  const book = bookParam === null || bookParam === '' ? undefined : Number(bookParam)
  const page = parsePage(params.get('page'))
  const books = useBooks()
  const query = { group, book, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useMeter(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const meta = res.data?.meta

  return (
    <>
      <p className="lede">{t.lede}</p>
      {res.data && !meta?.test && <p className="status">{t.noData}</p>}
      {res.data && meta?.test && <Tests data={res.data} />}

      <section aria-label={t.rankTitle}>
        <h2>{t.rankTitle}</h2>
        {meta?.min_lines != null && <p className="muted small">{t.rankNote(meta.min_lines)}</p>}
        <div className="toolbar">
          <label className="control">
            <span>{t.cols.group}</span>
            <select value={group ?? ''} onChange={(e) => set({ group: e.target.value || null })}>
              <option value="">{t.anyGroup}</option>
              {GROUPS.map((g) => (
                <option key={g} value={g}>
                  {t.groups[g]}
                </option>
              ))}
            </select>
          </label>
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
        </div>
        <PagedList
          res={res}
          empty={t.noData}
          summary={(data) => (
            <>
              {t.ranked(data.total)} · {m.pat.pageOf(page, pages)}
              {' · '}
              <ExportCsv
                all={{ list: 'meter', params: meterParams(query) }}
                filename={`meter-p${page}.csv`}
                rows={() =>
                  data.items.map((c) => ({
                    chapter: c.unit.label_en,
                    group: c.group,
                    lines: c.n_lines,
                    fall: c.fall,
                    rise: c.rise,
                    net: c.net,
                    share32: c.share32,
                    pct: c.pct,
                  }))
                }
              />
            </>
          )}
        >
          {(data, stale) => <ChapterTable rows={data.items} stale={stale} withGroup />}
        </PagedList>
      </section>
    </>
  )
}

function Tests({ data }: { data: MeterResponse }) {
  const t = useLocale().m.met
  const meta = data.meta
  const test = meta.test!
  const named = meta.named
  return (
    <>
      <section aria-label={t.testTitle}>
        <h2>{t.testTitle}</h2>
        <p className="small">
          {t.test(meta.min_stresses ?? 0, meta.max_stresses ?? 0, test.mean, test.pool_mean, test.pool_n, test.p, meta.test_poetic?.p ?? null)}
        </p>
        {meta.pool_quantile != null && <p className="muted small">{t.poolNote(meta.pool_quantile, meta.pool_prob ?? null)}</p>}
        <ChapterTable rows={[...data.test_chapters, ...data.control_chapters]} label={t.testTitle} />
        <p className="muted small">{t.testNote}</p>
        <p className="muted small">
          <strong>{t.controlTitle}.</strong> {t.control}
        </p>
      </section>
      {meta.groups && <Patterns data={data} />}
      {meta.grid && meta.grid.length > 0 && (
        <section aria-label={t.gridTitle}>
          <h2>{t.gridTitle}</h2>
          <div className="table-wrap" tabIndex={0} role="region" aria-label={t.gridTitle}>
            <table className="change-table">
              <thead>
                <tr>
                  <th>{t.grid.length}</th>
                  <th className="num">{t.grid.lam}</th>
                  <th className="num">{t.grid.pool}</th>
                  <th className="num">{t.grid.p}</th>
                  <th className="num">{t.grid.poeticP}</th>
                </tr>
              </thead>
              <tbody>
                {[{ min: meta.min_stresses!, max: meta.max_stresses!, mean: test.mean, pool_mean: test.pool_mean, pool_p: test.p, poetic_p: meta.test_poetic?.p ?? null }, ...meta.grid].map((g) => (
                  <tr key={`${g.min}-${g.max}`}>
                    <td className="num">
                      {g.min}–{g.max}
                    </td>
                    <td className="num">{x2(g.mean)}</td>
                    <td className="num">{x2(g.pool_mean)}</td>
                    <td className="num">{fp(g.pool_p)}</td>
                    <td className="num">{fp(g.poetic_p)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {named && named.p != null && (
        <section aria-label={t.namedTitle}>
          <h2>{t.namedTitle}</h2>
          <p className="small">{t.named(named.n, named.mean, named.pool_mean, named.p)}</p>
          <ChapterTable rows={data.named_chapters} label={t.namedTitle} />
        </section>
      )}
    </>
  )
}

function Patterns({ data }: { data: MeterResponse }) {
  const t = useLocale().m.met
  const groups = data.meta.groups!
  return (
    <section aria-label={t.patternsTitle}>
      <h2>{t.patternsTitle}</h2>
      <ul className="division-findings small">
        {GROUPS.filter((g) => groups[g]).map((g) => {
          const s = groups[g]!
          return (
            <li key={g}>
              <strong>{t.groups[g]}</strong> · {t.patterns(s.lines)}{' '}
              <span dir="ltr">{s.patterns.map(([p, n]) => `${p} ×${n}`).join(' · ')}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function ChapterTable({ rows, stale = '', withGroup = false, label }: { rows: MeterChapter[]; stale?: string; withGroup?: boolean; label?: string }) {
  const { m, locale } = useLocale()
  const t = m.met
  const table = (
    <table className={`change-table ${stale}`}>
      <thead>
        <tr>
          <th>{t.cols.chapter}</th>
          {withGroup && <th>{t.cols.group}</th>}
          <th className="num" title={t.colTitles.lines}>
            {t.cols.lines}
          </th>
          <th className="num" title={t.colTitles.fall}>
            {t.cols.fall}
          </th>
          <th className="num" title={t.colTitles.rise}>
            {t.cols.rise}
          </th>
          <th className="num" title={t.colTitles.net}>
            {t.cols.net}
          </th>
          <th className="num" title={t.colTitles.share32}>
            {t.cols.share32}
          </th>
          <th className="num" title={t.colTitles.pct}>
            {t.cols.pct}
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c) => (
          <tr key={c.unit.unit_id}>
            <td>
              <Link to={unitLink(c.unit.unit_id, '?halves=1&meter=1')}>{unitLabel(c.unit, locale)}</Link>
            </td>
            {withGroup && <td className="small">{t.groups[c.group]}</td>}
            <td className="num">{c.n_lines}</td>
            <td className="num">{pct(c.fall)}</td>
            <td className="num">{pct(c.rise)}</td>
            <td className="num">{x2(c.net)}</td>
            <td className="num">{pct(c.share32)}</td>
            <td className="num">{pct(c.pct)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
  return label ? (
    <div className="table-wrap" tabIndex={0} role="region" aria-label={label}>
      {table}
    </div>
  ) : (
    <div className="table-wrap">{table}</div>
  )
}

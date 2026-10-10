import { Link } from 'react-router'
import { useShifts } from '../api/hooks'
import { Segmented } from '../components/Controls'
import { PagedList } from '../components/Pager'
import { useLocale } from '../context/localeContext'
import { lemmaLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** Words whose dictionary senses or contextual uses differ most across the canon (§16.23). */
export function ShiftsPage() {
  const { m } = useLocale()
  const t = m.sen
  const [params, update] = useQueryParams()
  const by = params.get('by') === 'use' ? 'use' : 'sense'
  const all = params.get('q') === 'all'
  const page = parsePage(params.get('page'))
  const res = useShifts(by, all ? 1 : 0.05, PAGE_SIZE, (page - 1) * PAGE_SIZE)
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  return (
    <div className="page shifts-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      <p className="muted small">{t.caveat}</p>
      {res.data?.nmi_mean != null && res.data.nmi_null_mean != null && (
        <p className="muted small">{t.check(res.data.nmi_mean.toFixed(2), res.data.nmi_null_mean.toFixed(2))}</p>
      )}
      <div className="toolbar">
        <Segmented
          label={t.by}
          value={by}
          onChange={(v) => set({ by: v === 'sense' ? null : v })}
          options={(['sense', 'use'] as const).map((v) => ({ value: v, label: t.bys[v] }))}
        />
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => set({ q: e.target.checked ? 'all' : null })} />
          {t.includeAll}
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.empty}
        summary={(data) => (
          <>
            {t.ranked(data.total)} · {m.pat.pageOf(page, pages)}
          </>
        )}
      >
        {(data, stale) => (
          <div className="table-wrap">
            <table className={`change-table ${stale}`}>
              <thead>
                <tr>
                  <th>{t.word}</th>
                  <th className="num">{t.occurrences}</th>
                  <th className="num" title={t.shiftTitle}>
                    {t.shift}
                  </th>
                  <th className="num">{t.q}</th>
                  <th className="num">{by === 'sense' ? t.senses : t.uses}</th>
                  <th title={t.groupsTitle}>{data.group_order.map((g) => t.groups[g] ?? g).join(' · ')}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => {
                  const excess = by === 'sense' ? r.sense_excess : r.use_excess
                  const q = by === 'sense' ? r.sense_q : r.use_q
                  const most = Math.max(1, ...Object.values(r.groups))
                  return (
                    <tr key={r.lemma}>
                      <td>
                        <Link to={`${lemmaLink(r.lemma)}#senses`}>
                          <span dir="rtl" lang="he" className="he">
                            {r.he_lemma}
                          </span>
                        </Link>
                      </td>
                      <td className="num">{m.num(r.n)}</td>
                      <td className="num">{excess?.toFixed(2) ?? '—'}</td>
                      <td className="num">{q == null ? '—' : q < 0.001 ? '< 0.001' : q.toFixed(3)}</td>
                      <td className="num">{by === 'sense' ? r.n_senses : r.k}</td>
                      <td>
                        <span className="group-strip" aria-label={t.groupsTitle}>
                          {data.group_order.map((g) => (
                            <span
                              key={g}
                              className="group-cell"
                              title={`${t.groups[g] ?? g}: ${r.groups[g] ?? 0}`}
                              style={{ opacity: 0.15 + (0.85 * (r.groups[g] ?? 0)) / most }}
                            />
                          ))}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </PagedList>
    </div>
  )
}

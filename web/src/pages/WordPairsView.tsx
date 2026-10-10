import { Link } from 'react-router'
import { useWordPairs, wordPairsParams } from '../api/hooks'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { useLocale } from '../context/localeContext'
import { lemmaLink, unitLink } from '../lib/links'
import { unitLabel } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** Fixed word pairs: lemmas that answer each other across the two members of parallel lines. */
export function WordPairsView() {
  const { m, locale } = useLocale()
  const t = m.pat.wordPairs
  const [params, update] = useQueryParams()
  const page = parsePage(params.get('page'))
  const all = params.get('pq') === 'all'
  const query = { maxQ: all ? undefined : 0.05, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
  const res = useWordPairs(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const he = (s: string) => (
    <span className="he" dir="rtl" lang="he">
      {s}
    </span>
  )
  return (
    <>
      <p className="lede">{t.lede}</p>
      <div className="toolbar">
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => update({ pq: e.target.checked ? 'all' : null, page: null })} />
          {m.pat.includeQ}
        </label>
      </div>
      <PagedList
        res={res}
        empty={t.empty}
        summary={(data) => (
          <>
            {m.pat.pairs(data.total)} · {m.pat.pageOf(page, pages)}
            {' · '}
            <ExportCsv
            all={{ list: 'word-pairs', params: wordPairsParams(query) }}
            filename={`word-pairs-p${page}.csv`}
            rows={() =>
            data.items.map((w) => ({ first: w.a.he_lemma, second: w.b.he_lemma, times: w.n, expected: w.expected, reverse: w.reverse, q: w.q }))
            }
            />
          </>
        )}
      >
        {(data, stale) => (
          <div className="table-wrap">
            <table className={`change-table ${stale}`}>
              <thead>
                <tr>
                  <th>{t.first}</th>
                  <th aria-hidden="true" />
                  <th>{t.second}</th>
                  <th className="num" title={t.linesTitle}>
                    {t.lines}
                  </th>
                  <th className="num" title={t.reversedTitle}>
                    {t.reversed}
                  </th>
                  <th>q</th>
                  <th>{t.examples}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((w) => (
                  <tr key={`${w.a.lemma}|${w.b.lemma}`}>
                    <td>
                      <Link to={lemmaLink(w.a.lemma)}>{he(w.a.he_lemma)}</Link>
                    </td>
                    <td className="muted" aria-hidden="true">
                      //
                    </td>
                    <td>
                      <Link to={lemmaLink(w.b.lemma)}>{he(w.b.he_lemma)}</Link>
                    </td>
                    <td className="num">
                      {w.n} <span className="muted small">/ {w.expected.toFixed(1)}</span>
                    </td>
                    <td className="num">{w.reverse}</td>
                    <td className={`small ${w.q <= 0.05 ? 'q-strong' : 'muted'}`}>{m.q(w.q)}</td>
                    <td className="change-examples small">
                      {w.examples.slice(0, 3).map((e) => (
                        <Link key={e.verse_id} to={unitLink(`v:${e.verse_id}`, '?halves=1')}>
                          {unitLabel(e, locale)}
                        </Link>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PagedList>
    </>
  )
}

import { Link } from 'react-router'
import { useWordPairs } from '../api/hooks'
import { ExportCsv } from '../components/ExportCsv'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { qLabel } from '../lib/format'
import { lemmaLink, unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50

/** Fixed word pairs: lemmas that answer each other across the two members of parallel lines. */
export function WordPairsView() {
  const [params, update] = useQueryParams()
  const page = parsePage(params.get('page'))
  const all = params.get('pq') === 'all'
  const res = useWordPairs({ maxQ: all ? undefined : 0.05, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const he = (s: string) => (
    <span className="he" dir="rtl" lang="he">
      {s}
    </span>
  )
  return (
    <>
      <p className="lede">
        Hebrew poets answer a word in the first half of a line with a fixed partner in the second: ארץ // תבל, יעקב //
        ישראל, צדיק // רשע. Counted over every line whose halves score as parallel (and pairs of verses that form one line),
        these are the lemma pairs found together across the halves far more often than their frequencies predict, in at
        least three chapters.
      </p>
      <div className="toolbar">
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => update({ pq: e.target.checked ? 'all' : null, page: null })} />
          Include q &gt; 0.05
        </label>
      </div>
      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No word pairs.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} pairs · page {page} of {pages}
            {' · '}
            <ExportCsv
              filename={`word-pairs-p${page}.csv`}
              rows={() =>
                res.data.items.map((w) => ({ first: w.a.he_lemma, second: w.b.he_lemma, times: w.n, expected: w.expected, reverse: w.reverse, q: w.q }))
              }
            />
          </p>
          <div className="table-wrap">
            <table className={`change-table ${res.isPlaceholderData ? 'stale' : ''}`}>
              <thead>
                <tr>
                  <th>First half</th>
                  <th aria-hidden="true" />
                  <th>Second half</th>
                  <th className="num" title="Parallel lines with the pair / expected by chance">
                    Lines
                  </th>
                  <th className="num" title="The pair in the other order">
                    Reversed
                  </th>
                  <th>q</th>
                  <th>Examples</th>
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((w) => (
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
                    <td className={`small ${w.q <= 0.05 ? 'q-strong' : 'muted'}`}>{qLabel(w.q)}</td>
                    <td className="change-examples small">
                      {w.examples.slice(0, 3).map((e) => (
                        <Link key={e.verse_id} to={unitLink(`v:${e.verse_id}`, '?halves=1')}>
                          {e.label_en}
                        </Link>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={page} pages={pages} onPage={(p) => update({ page: p === 1 ? null : String(p) }, false)} />
        </>
      )}
    </>
  )
}

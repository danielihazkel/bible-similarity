import { Link } from 'react-router'
import { useBooks, useRewriteProfiles, useRewrites } from '../api/hooks'
import type { Rewrite, RewriteOp, RewriteProfile } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { Pager } from '../components/Pager'
import { ErrorBox, Loading } from '../components/Status'
import { qLabel } from '../lib/format'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const OPS: { value: RewriteOp; label: string; hint: string }[] = [
  { value: 'substitution', label: 'Substituted', hint: 'one word regularly replaced by another' },
  { value: 'omitted', label: 'Dropped', hint: 'a word the later text regularly leaves out' },
  { value: 'added', label: 'Added', hint: 'a word the later text regularly adds' },
]
const Q_TITLE = 'Benjamini–Hochberg q over all book pairs and changes'

const pairKey = (p: { a_book: number; b_book: number }) => `${p.a_book}-${p.b_book}`

/**
 * Changes one book makes consistently against another: for every pair of books with parallel
 * passages, the replacements, omissions and additions that recur more than the pair's overall
 * rate of change explains (G², BH q), plus the pair's profile of changes.
 */
export function RewritesView() {
  const [params, update] = useQueryParams()
  const books = useBooks()
  const profiles = useRewriteProfiles()
  const name = (id: number) => books.data?.find((b) => b.book_id === id)?.name ?? String(id)
  const pairParam = params.get('pair')
  const profile = profiles.data?.find((p) => pairKey(p) === pairParam)
  const rawOp = params.get('rop') as RewriteOp | null
  const op = OPS.some((o) => o.value === rawOp) ? rawOp! : undefined
  const all = params.get('rq') === 'all'
  const page = parsePage(params.get('page'))
  const res = useRewrites({
    aBook: profile?.a_book,
    bBook: profile?.b_book,
    op,
    maxQ: all ? undefined : 0.05,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <>
      <p className="muted small">
        A change counts as a habit when it recurs between two books more often than their overall rate of change
        explains: the later book's word, given the earlier one, compared by log-likelihood (G²), with q corrected for
        testing every change of every book pair.
      </p>
      <div className="toolbar">
        <label className="control">
          <span>Books</span>
          <select value={profile ? pairKey(profile) : ''} onChange={(e) => set({ pair: e.target.value || null })}>
            <option value="">All book pairs</option>
            {profiles.data?.map((p) => (
              <option key={pairKey(p)} value={pairKey(p)}>
                {p.a_book === p.b_book ? `${name(p.a_book)} (repeats within)` : `${name(p.a_book)} → ${name(p.b_book)}`} ·{' '}
                {p.verse_pairs} verse pairs
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>Change</span>
          <select value={op ?? ''} onChange={(e) => set({ rop: e.target.value || null })}>
            <option value="">Any</option>
            {OPS.map((o) => (
              <option key={o.value} value={o.value} title={o.hint}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => set({ rq: e.target.checked ? 'all' : null })} />
          Include q &gt; 0.05
        </label>
      </div>
      {profile && <Profile p={profile} from={name(profile.a_book)} to={name(profile.b_book)} />}

      {res.isPending ? (
        <Loading />
      ) : res.error ? (
        <ErrorBox error={res.error} />
      ) : res.data.items.length === 0 ? (
        <p className="status">No systematic changes for these filters.</p>
      ) : (
        <>
          <p className="muted small">
            {res.data.total.toLocaleString()} changes · page {page} of {pages}
            {' · '}
            <ExportCsv
              filename={`rewrites-p${page}.csv`}
              rows={() =>
                res.data.items.map((r) => ({
                  earlier_book: name(r.a_book),
                  later_book: name(r.b_book),
                  change: r.op,
                  earlier: r.a_he ?? '',
                  later: r.b_he ?? '',
                  times: r.n,
                  of: r.base,
                  g2: r.g2,
                  q: r.q,
                }))
              }
            />
          </p>
          <div className="table-wrap">
            <table className={`change-table ${res.isPlaceholderData ? 'stale' : ''}`}>
              <thead>
                <tr>
                  {!profile && <th>Books</th>}
                  <th>Earlier</th>
                  <th aria-hidden="true" />
                  <th>Later</th>
                  <th className="num" title="Times this change occurs / words it could apply to">
                    Times
                  </th>
                  <th className="num">G²</th>
                  <th>q</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {res.data.items.map((r) => (
                  <Row key={`${pairKey(r)}|${r.op}|${r.a_key}|${r.b_key}`} r={r} showBooks={!profile} name={name} />
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

function Profile({ p, from, to }: { p: RewriteProfile; from: string; to: string }) {
  const per100 = (n: number) => ((100 * n) / Math.max(1, p.a_words)).toFixed(1)
  const spell = p.to_plene + p.to_defective
  return (
    <dl className="rewrite-profile" aria-label="How these books differ">
      <div>
        <dt>Parallel verses</dt>
        <dd>
          {p.verse_pairs} pairs, {p.a_words.toLocaleString()} → {p.b_words.toLocaleString()} words
        </dd>
      </div>
      <div>
        <dt>Per 100 words of {from}</dt>
        <dd>
          {per100(p.substitution)} substituted · {per100(p.omitted)} dropped · {per100(p.added)} added ·{' '}
          {per100(p.form)} other form · {per100(p.spelling)} spelling
        </dd>
      </div>
      {spell > 0 && (
        <div>
          <dt>Spelling</dt>
          <dd>
            {to} writes a vowel letter (ו / י) {from} lacks {p.to_plene}× and drops one {p.to_defective}× (
            {Math.round((100 * p.to_plene) / spell)}% fuller)
          </dd>
        </div>
      )}
    </dl>
  )
}

function Row({ r, showBooks, name }: { r: Rewrite; showBooks: boolean; name: (id: number) => string }) {
  const word = (he: string | null) =>
    he === null ? (
      <span className="muted">—</span>
    ) : (
      <span className="he" dir="rtl" lang="he">
        {he}
      </span>
    )
  const examples = `/changes?op=${r.op}&a=${r.a_book}&b=${r.b_book}`
  return (
    <tr>
      {showBooks && (
        <td className="small">
          {name(r.a_book)} → {name(r.b_book)}
        </td>
      )}
      <td>{word(r.a_he)}</td>
      <td className="muted" aria-hidden="true">
        →
      </td>
      <td>{word(r.b_he)}</td>
      <td className="num" title={r.rate === null ? undefined : `${Math.round(r.rate * 100)}% of the time`}>
        {r.n} / {r.base}
      </td>
      <td className="num">{r.g2.toFixed(1)}</td>
      <td className={`small ${r.q <= 0.05 ? 'q-strong' : 'muted'}`} title={Q_TITLE}>
        {qLabel(r.q)}
      </td>
      <td className="small">
        <Link to={examples}>Examples</Link>
      </td>
    </tr>
  )
}

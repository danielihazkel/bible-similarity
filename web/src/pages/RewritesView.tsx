import { Link } from 'react-router'
import { useBooks, useRewriteProfiles, useRewrites, rewritesParams } from '../api/hooks'
import type { Rewrite, RewriteOp, RewriteProfile } from '../api/types'
import { ExportCsv } from '../components/ExportCsv'
import { PagedList } from '../components/Pager'
import { useLocale } from '../context/localeContext'
import { bookName } from '../lib/names'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 50
const OPS: RewriteOp[] = ['substitution', 'omitted', 'added']

const pairKey = (p: { a_book: number; b_book: number }) => `${p.a_book}-${p.b_book}`

/**
 * Changes one book makes consistently against another: for every pair of books with parallel
 * passages, the replacements, omissions and additions that recur more than the pair's overall
 * rate of change explains (G², BH q), plus the pair's profile of changes.
 */
export function RewritesView() {
  const { m, locale } = useLocale()
  const [params, update] = useQueryParams()
  const books = useBooks()
  const profiles = useRewriteProfiles()
  const book = (id: number) => books.data?.find((b) => b.book_id === id)
  // CSV rows keep the English names; the page shows the interface language's
  const nameEn = (id: number) => book(id)?.name ?? String(id)
  const name = (id: number) => {
    const b = book(id)
    return b ? bookName(b, locale) : String(id)
  }
  const pairParam = params.get('pair')
  const profile = profiles.data?.find((p) => pairKey(p) === pairParam)
  const rawOp = params.get('rop') as RewriteOp | null
  const op = OPS.some((o) => o === rawOp) ? rawOp! : undefined
  const all = params.get('rq') === 'all'
  const page = parsePage(params.get('page'))
  const query = {
    aBook: profile?.a_book,
    bBook: profile?.b_book,
    op,
    maxQ: all ? undefined : 0.05,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  }
  const res = useRewrites(query)
  const pages = res.data ? Math.max(1, Math.ceil(res.data.total / PAGE_SIZE)) : 1
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })

  return (
    <>
      <p className="muted small">{m.par.rewrites.intro}</p>
      <div className="toolbar">
        <label className="control">
          <span>{m.par.rewrites.books}</span>
          <select value={profile ? pairKey(profile) : ''} onChange={(e) => set({ pair: e.target.value || null })}>
            <option value="">{m.par.rewrites.allPairs}</option>
            {profiles.data?.map((p) => (
              <option key={pairKey(p)} value={pairKey(p)}>
                {p.a_book === p.b_book ? m.par.rewrites.within(name(p.a_book)) : m.par.rewrites.pair(name(p.a_book), name(p.b_book))}{' '}
                · {m.par.rewrites.optionPairs(p.verse_pairs)}
              </option>
            ))}
          </select>
        </label>
        <label className="control">
          <span>{m.par.rewrites.change}</span>
          <select value={op ?? ''} onChange={(e) => set({ rop: e.target.value || null })}>
            <option value="">{m.par.rewrites.any}</option>
            {OPS.map((o) => (
              <option key={o} value={o} title={m.par.rewrites.ops[o].hint}>
                {m.par.rewrites.ops[o].label}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={all} onChange={(e) => set({ rq: e.target.checked ? 'all' : null })} />
          {m.par.includeQ}
        </label>
      </div>
      {profile && <Profile p={profile} from={name(profile.a_book)} to={name(profile.b_book)} />}

      <PagedList
        res={res}
        empty={m.par.rewrites.none}
        summary={(data) => (
          <>
            {m.par.rewrites.page(data.total, page, pages)}
            {' · '}
            <ExportCsv
            all={{ list: 'rewrites', params: rewritesParams(query) }}
            filename={`rewrites-p${page}.csv`}
            rows={() =>
            data.items.map((r) => ({
            earlier_book: nameEn(r.a_book),
            later_book: nameEn(r.b_book),
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
          </>
        )}
      >
        {(data, stale) => (
          <div className="table-wrap">
            <table className={`change-table ${stale}`}>
              <thead>
                <tr>
                  {!profile && <th>{m.par.rewrites.books}</th>}
                  <th>{m.par.changes.earlier}</th>
                  <th aria-hidden="true" />
                  <th>{m.par.changes.later}</th>
                  <th className="num" title={m.par.rewrites.timesTitle}>
                    {m.par.changes.times}
                  </th>
                  <th className="num">G²</th>
                  <th>q</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <Row key={`${pairKey(r)}|${r.op}|${r.a_key}|${r.b_key}`} r={r} showBooks={!profile} name={name} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PagedList>
    </>
  )
}

function Profile({ p, from, to }: { p: RewriteProfile; from: string; to: string }) {
  const { m } = useLocale()
  const per100 = (n: number) => ((100 * n) / Math.max(1, p.a_words)).toFixed(1)
  const spell = p.to_plene + p.to_defective
  return (
    <dl className="rewrite-profile" aria-label={m.par.rewrites.profile}>
      <div>
        <dt>{m.par.rewrites.parallelVerses}</dt>
        <dd>{m.par.rewrites.profilePairs(p.verse_pairs, p.a_words, p.b_words)}</dd>
      </div>
      <div>
        <dt>{m.par.rewrites.per100Of(from)}</dt>
        <dd>
          {m.par.rewrites.per100(
            per100(p.substitution),
            per100(p.omitted),
            per100(p.added),
            per100(p.form),
            per100(p.spelling),
          )}
        </dd>
      </div>
      {spell > 0 && (
        <div>
          <dt>{m.par.rewrites.spelling}</dt>
          <dd>
            {m.par.rewrites.spellingText(to, from, p.to_plene, p.to_defective, Math.round((100 * p.to_plene) / spell))}
          </dd>
        </div>
      )}
    </dl>
  )
}

function Row({ r, showBooks, name }: { r: Rewrite; showBooks: boolean; name: (id: number) => string }) {
  const { m } = useLocale()
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
          {m.par.rewrites.pair(name(r.a_book), name(r.b_book))}
        </td>
      )}
      <td>{word(r.a_he)}</td>
      <td className="muted" aria-hidden="true">
        {m.par.arrow}
      </td>
      <td>{word(r.b_he)}</td>
      <td className="num" title={r.rate === null ? undefined : m.par.rewrites.rateTitle(r.rate)}>
        {r.n} / {r.base}
      </td>
      <td className="num">{r.g2.toFixed(1)}</td>
      <td className={`small ${r.q <= 0.05 ? 'q-strong' : 'muted'}`} title={m.par.rewrites.qTitle}>
        {m.q(r.q)}
      </td>
      <td className="small">
        <Link to={examples}>{m.par.changes.examples}</Link>
      </td>
    </tr>
  )
}

import { Link } from 'react-router'
import { useRetold, useRetoldItems } from '../api/hooks'
import type { RetoldGroup, RetoldOrder, RetoldPair, RetoldResponse, RetoldSide } from '../api/types'
import { Segmented } from '../components/Controls'
import { DiffLegend } from '../components/DiffLegend'
import { HebrewText } from '../components/HebrewText'
import { PagedList } from '../components/Pager'
import { UnitName } from '../components/UnitName'
import { useLocale } from '../context/localeContext'
import { diffHighlight } from '../lib/highlight'
import { readLink, unitLink } from '../lib/links'
import { parsePage, useQueryParams } from '../lib/urlState'

const PAGE_SIZE = 20
const GROUPS: RetoldGroup[] = ['retold', 'repeated', 'carried', 'told', 'narrated', 'unclear']
const ORDERS: RetoldOrder[] = ['canon', 'most', 'least']
const isGroup = (x: string | null): x is RetoldGroup => GROUPS.includes(x as RetoldGroup)

/** Retold speech (§16.68): passages told again, by another speaker, the same one or the narrator,
 * set side by side word by word; the claim and the known retellings. */
export function RetoldPage() {
  const { m } = useLocale()
  const t = m.rt
  const res = useRetold()
  const d = res.data
  return (
    <div className="page retold-page">
      <h1>{t.title}</h1>
      <p className="lede">{t.lede}</p>
      {res.isError ? (
        <p className="status">{t.notComputed}</p>
      ) : !d ? (
        <p className="status">{m.status.loading}</p>
      ) : (
        <>
          <Checks d={d} />
          <Groups d={d} />
          <Passages />
          <p className="muted small">{t.method}</p>
        </>
      )}
    </div>
  )
}

function Verdict({ holds }: { holds: boolean }) {
  const t = useLocale().m.rt
  return <span className={`dv-verdict ${holds ? 'holds' : 'fails'}`}>{holds ? t.holds : t.fails}</span>
}

function Checks({ d }: { d: RetoldResponse }) {
  const t = useLocale().m.rt
  const [a, b] = d.claim
  const ra = d.rates[a]
  const rb = d.rates[b]
  return (
    <section aria-labelledby="rt-checks">
      <h2 id="rt-checks">{t.checksTitle}</h2>
      <div className="dv-checks">
        <article className="dv-check">
          <h3>
            {t.claim.title} <Verdict holds={d.holds} />
          </h3>
          {ra != null && rb != null && <p>{t.claim.text(ra, rb, d.groups[a] ?? 0, d.groups[b] ?? 0, d.p)}</p>}
        </article>
        <article className="dv-check">
          <h3>
            {t.known.title} <Verdict holds={d.known_holds} />
          </h3>
          <p>{t.known.text(d.known_found, d.known.length)}</p>
          <ul className="brk-known small">
            {d.known.map((k) => (
              <li key={`${k.source}|${k.retelling}`}>
                {k.source} → {k.retelling}: {k.found && k.rate !== null ? t.known.found(k.rate) : t.known.missing}
              </li>
            ))}
          </ul>
        </article>
      </div>
    </section>
  )
}

function Groups({ d }: { d: RetoldResponse }) {
  const t = useLocale().m.rt
  return (
    <section aria-labelledby="rt-groups">
      <h2 id="rt-groups">{t.groupsTitle}</h2>
      <table className="change-table rt-groups">
        <thead>
          <tr>
            <th scope="col">{t.cols.group}</th>
            <th scope="col" className="num">
              {t.cols.pairs}
            </th>
            <th scope="col" className="num">
              {t.cols.rate}
            </th>
          </tr>
        </thead>
        <tbody>
          {GROUPS.map((g) => {
            const r = d.rates[g]
            return (
              <tr key={g} className={d.claim.includes(g) ? 'rt-claim' : undefined}>
                <th scope="row">{t.groups[g]}</th>
                <td className="num">{d.groups[g] ?? 0}</td>
                <td className="num">{r == null ? '—' : `${Math.round(r * 100)}%`}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}

function Passages() {
  const t = useLocale().m.rt
  const [params, update] = useQueryParams()
  const gp = params.get('group')
  const group = isGroup(gp) ? gp : undefined
  const op = params.get('order')
  const order: RetoldOrder = op === 'most' || op === 'least' ? op : 'canon'
  const known = params.get('known') === '1'
  const page = parsePage(params.get('page'))
  const set = (changes: Record<string, string | null>) => update({ ...changes, page: null })
  const res = useRetoldItems({ group, known, order, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE })
  return (
    <section aria-labelledby="rt-list">
      <h2 id="rt-list">{t.listTitle}</h2>
      <div className="toolbar">
        <Segmented<RetoldGroup | 'all'>
          label={t.show.label}
          value={group ?? 'all'}
          options={[{ value: 'all', label: t.show.all }, ...GROUPS.map((g) => ({ value: g, label: t.groups[g] }))]}
          onChange={(v) => set({ group: v === 'all' ? null : v })}
        />
        <Segmented<RetoldOrder> label={t.order.label} value={order} options={ORDERS.map((v) => ({ value: v, label: t.order[v] }))} onChange={(v) => set({ order: v === 'canon' ? null : v })} />
        <label className="check">
          <input type="checkbox" checked={known} onChange={(e) => set({ known: e.target.checked ? '1' : null })} />
          {t.knownOnly}
        </label>
      </div>
      <DiffLegend />
      <PagedList res={res} empty={t.empty} summary={(p, n, pages) => `${t.count(p.total)} · ${t.pageOf(n, pages)}`}>
        {(p, stale) => (
          <ol className={`hits rt-list ${stale}`}>
            {p.items.map((r) => (
              <PairItem key={r.pair} r={r} />
            ))}
          </ol>
        )}
      </PagedList>
    </section>
  )
}

function Teller({ side }: { side: RetoldSide }) {
  const t = useLocale().m.rt
  if (side.kind === 'narration') return <>{t.narrator}</>
  if (!side.teller) return <>{t.unknown}</>
  if (side.teller.key === 'divine') return <>{t.god}</>
  return (
    <span dir="rtl" lang="he" className="he">
      {side.teller.he ?? side.teller.key}
    </span>
  )
}

function Span({ side }: { side: RetoldSide }) {
  const first = side.verses[0]
  const last = side.verses[side.verses.length - 1]
  if (!first || !last) return null
  return (
    <Link className="verse-ref" to={unitLink(`v:${first.verse_id}`)}>
      <UnitName en={first.ref} he={first.ref_he} />
      {last.verse_id !== first.verse_id && (
        <>
          {' – '}
          <UnitName en={last.ref} he={last.ref_he} />
        </>
      )}
    </Link>
  )
}

function PairItem({ r }: { r: RetoldPair }) {
  const t = useLocale().m.rt
  const a = r.source.verses[0]
  const b = r.retelling.verses[0]
  return (
    <li className={`hit rt-pair rt-${r.group}`}>
      <div className="hit-head">
        <Span side={r.source} /> → <Span side={r.retelling} /> <span className="type-tag">{t.groups[r.group]}</span>{' '}
        <span className="small">{t.rate(r.rate, r.n_ops)}</span>
        {r.known && <span className="muted small"> · {t.knownTag}</span>}
      </div>
      <p className="small rt-teller">
        {t.first} <Teller side={r.source} />
      </p>
      {r.source.verses.map((v, i) => (
        <p key={v.verse_id} className="hit-text">
          <HebrewText verse={v} highlight={diffHighlight(r.source.marks[i])} />
        </p>
      ))}
      <p className="small rt-teller">
        {t.again} <Teller side={r.retelling} />
      </p>
      {r.retelling.verses.map((v, i) => (
        <p key={v.verse_id} className="hit-text">
          <HebrewText verse={v} highlight={diffHighlight(r.retelling.marks[i])} />
        </p>
      ))}
      {a && b && (
        <p className="small brk-links">
          <Link to={`/compare?a=${encodeURIComponent(`v:${a.verse_id}`)}&b=${encodeURIComponent(`v:${b.verse_id}`)}&marks=changes`}>{t.compare}</Link> · <Link to={readLink(r.unit_id)}>{t.read}</Link>
        </p>
      )}
    </li>
  )
}

import { useMemo } from 'react'
import { Link } from 'react-router'
import { useBooks, useCommunity, useNetwork, useUnitNetwork } from '../api/hooks'
import type { Book, CommunityResponse, NetworkCommunity, NetworkNode, UnitType } from '../api/types'
import { Segmented } from '../components/Controls'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale, useT } from '../context/localeContext'
import { unitLink } from '../lib/links'
import { bookName, unitLabel } from '../lib/names'
import { useQueryParams } from '../lib/urlState'
import { DirectionsView } from './DirectionsView'

const TYPES: UnitType[] = ['chapter', 'pericope']
const SECTIONS = ['Torah', 'Prophets', 'Writings']
const SECTION_HUES = [210, 25, 140]
const sectionName = (names: Record<string, string>, s: string | undefined) => (s === undefined ? undefined : (names[s] ?? s))
const W = 960
const H = 620
const PAD = 28

/** Passages as a network of echoes: communities that echo each other, the most echoed passages, and
 * (`?view=directions`) who echoes whom across books. */
export function NetworkPage() {
  const m = useT()
  const [params, update] = useQueryParams()
  const view = params.get('view') === 'directions' ? 'directions' : 'communities'
  return (
    <div className="page network-page">
      <h1>{m.ov.network.title}</h1>
      <Segmented
        label={m.echo.viewLabel}
        value={view}
        options={[
          { value: 'communities', label: m.echo.views.communities },
          { value: 'directions', label: m.echo.views.directions },
        ]}
        onChange={(v) => update({ view: v === 'directions' ? 'directions' : null, unit: null, page: null }, false)}
      />
      {view === 'directions' ? <DirectionsView /> : <Communities />}
    </div>
  )
}

function Communities() {
  const m = useT()
  const [params, update] = useQueryParams()
  const raw = params.get('type') as UnitType | null
  const unitType = raw && TYPES.includes(raw) ? raw : 'chapter'
  const focusUnit = params.get('unit') ?? undefined
  const focus = useUnitNetwork(focusUnit)
  const cParam = params.get('c')
  const net = useNetwork(unitType)
  const books = useBooks()
  const community =
    cParam !== null && cParam !== '' && Number.isInteger(Number(cParam))
      ? Number(cParam)
      : focus.data && focus.data.node.unit.unit_type === unitType
        ? focus.data.node.community
        : 0
  const detail = useCommunity(unitType, net.data ? community : undefined)
  const bookOf = useMemo(() => new Map((books.data ?? []).map((b) => [b.book_id, b])), [books.data])

  return (
    <>
      <p className="lede">
        {m.ov.network.ledeLinked(unitType)}
        <em>{m.ov.network.communities}</em>
        {m.ov.network.ledeCommunities}
        <em>{m.ov.network.central}</em>
        {m.ov.network.ledeCentral}
      </p>
      <div className="toolbar">
        <Segmented
          label={m.units.unitType}
          value={unitType}
          onChange={(t) => update({ type: t === 'chapter' ? null : t, c: null, unit: null })}
          options={TYPES.map((t) => ({ value: t, label: m.units.type(t) }))}
        />
      </div>
      {net.isPending ? (
        <Loading />
      ) : net.error ? (
        <ErrorBox error={net.error} />
      ) : (
        <>
          <div className="network-grid">
            <section aria-label={m.ov.network.communities}>
              <h2>{m.ov.network.nCommunities(net.data.communities.length)}</h2>
              <ul className="community-list">
                {net.data.communities.map((c) => (
                  <li key={c.community}>
                    <button
                      type="button"
                      aria-pressed={c.community === community}
                      className={c.community === community ? 'on' : undefined}
                      onClick={() => update({ c: String(c.community) }, false)}
                    >
                      <CommunityLabel c={c} bookOf={bookOf} />
                    </button>
                  </li>
                ))}
              </ul>
            </section>
            <section aria-label={m.ov.network.graph}>
              {detail.isPending ? (
                <Loading />
              ) : detail.error ? (
                <ErrorBox error={detail.error} />
              ) : (
                <CommunityGraph data={detail.data} bookOf={bookOf} focus={focusUnit} />
              )}
            </section>
          </div>
          <section aria-label={m.ov.network.mostEchoedLabel}>
            <h2>{m.ov.network.mostEchoed(unitType)}</h2>
            <NodeTable nodes={net.data.central} bookOf={bookOf} onCommunity={(k) => update({ c: String(k) }, false)} />
          </section>
        </>
      )}
    </>
  )
}

function CommunityLabel({ c, bookOf }: { c: NetworkCommunity; bookOf: Map<number, Book> }) {
  const { m, locale } = useLocale()
  const name = (id: number) => {
    const b = bookOf.get(id)
    return b ? bookName(b, locale) : id
  }
  return (
    <>
      <span className="community-size">{c.size}</span>
      <span className="community-text">
        <span className="he" dir="rtl" lang="he">
          {c.lemmas.map((l) => l.he_lemma).join(' · ')}
        </span>
        <span className="muted small">
          {c.books
            .slice(0, 3)
            .map((b) => `${name(b.book_id)} ${b.n_verses}`)
            .join(', ')}
          {c.books.length > 3 && m.ov.network.moreBooks(c.books.length - 3)}
        </span>
      </span>
    </>
  )
}

function CommunityGraph({ data, bookOf, focus }: { data: CommunityResponse; bookOf: Map<number, Book>; focus?: string }) {
  const { m, locale } = useLocale()
  const { nodes, edges } = data
  const at = new Map(nodes.map((n) => [n.unit.unit_id, n]))
  const maxRank = Math.max(...nodes.map((n) => n.pagerank))
  const px = (n: NetworkNode) => PAD + n.x * (W - 2 * PAD)
  const py = (n: NetworkNode) => PAD + n.y * (H - 2 * PAD)
  const radius = (n: NetworkNode) => 3 + 9 * Math.sqrt(n.pagerank / maxRank)
  const hue = (n: NetworkNode) => SECTION_HUES[Math.max(0, SECTIONS.indexOf(bookOf.get(n.unit.book_id)?.section ?? 'Torah'))]
  const labelled = new Set(
    [...nodes]
      .sort((a, b) => b.pagerank - a.pagerank)
      .slice(0, 12)
      .map((n) => n.unit.unit_id),
  )
  if (focus) labelled.add(focus)
  return (
    <>
      <h2>{m.ov.network.communityOf(data.community.size, data.unit_type)}</h2>
      <p className="muted small">{m.ov.network.legend}</p>
      <p className="section-legend small" aria-hidden="true">
        {SECTIONS.map((s, i) => (
          <span key={s}>
            <span className="swatch" style={{ background: `hsl(${SECTION_HUES[i]}, 62%, 48%)` }} /> {m.units.sections[s] ?? s}
          </span>
        ))}
      </p>
      <svg className="network-graph" viewBox={`0 0 ${W} ${H}`} role="group" aria-label={m.ov.network.graphLabel} direction="ltr">
        <g className="edges" aria-hidden="true">
          {edges.map((e) => {
            const a = at.get(e.a)
            const b = at.get(e.b)
            if (!a || !b) return null
            return <line key={`${e.a}|${e.b}`} x1={px(a)} y1={py(a)} x2={px(b)} y2={py(b)} strokeOpacity={0.1 + 0.45 * e.weight} />
          })}
        </g>
        {nodes.map((n) => {
          const on = n.unit.unit_id === focus
          const label = unitLabel(n.unit, locale)
          return (
            // a router Link inside <svg> renders an SVG <a>, keeping client-side navigation
            <Link key={n.unit.unit_id} to={unitLink(n.unit.unit_id)} aria-label={m.ov.network.node(label, n.partners)}>
              <title>{m.ov.network.nodeTitle(label, n.partners, n.cross_book)}</title>
              <circle
                cx={px(n)}
                cy={py(n)}
                r={radius(n) + (on ? 3 : 0)}
                fill={`hsl(${hue(n)}, 62%, 48%)`}
                className={on ? 'node focus' : 'node'}
              />
              {labelled.has(n.unit.unit_id) && (
                <text x={px(n) + radius(n) + 3} y={py(n) + 4} className="node-label">
                  {label}
                </text>
              )}
            </Link>
          )
        })}
      </svg>
      <details className="community-members">
        <summary>{m.ov.network.allPassages(nodes.length)}</summary>
        <NodeTable nodes={nodes} bookOf={bookOf} />
      </details>
    </>
  )
}

function NodeTable({
  nodes,
  bookOf,
  onCommunity,
}: {
  nodes: NetworkNode[]
  bookOf: Map<number, Book>
  onCommunity?: (k: number) => void
}) {
  const { m, locale } = useLocale()
  return (
    <div className="table-wrap">
      <table className="rank-table">
        <thead>
          <tr>
            <th scope="col">{m.ov.network.passage}</th>
            <th scope="col" className="num">
              {m.ov.network.echoes}
            </th>
            <th scope="col" className="num" title={m.ov.network.otherBooksTitle}>
              {m.ov.network.otherBooks}
            </th>
            {onCommunity && <th scope="col">{m.ov.network.community}</th>}
          </tr>
        </thead>
        <tbody>
          {nodes.map((n) => (
            <tr key={n.unit.unit_id}>
              <th scope="row">
                <Link to={unitLink(n.unit.unit_id)}>{unitLabel(n.unit, locale)}</Link>
                {locale === 'en' && (
                  <>
                    {' '}
                    <span className="he-label" dir="rtl" lang="he">
                      {n.unit.label_he}
                    </span>
                  </>
                )}
                <span className="muted small"> {sectionName(m.units.sections, bookOf.get(n.unit.book_id)?.section)}</span>
              </th>
              <td className="num">{n.partners}</td>
              <td className="num">{Math.round(n.cross_book * 100)}%</td>
              {onCommunity && (
                <td>
                  <button type="button" className="linkish" onClick={() => onCommunity(n.community)}>
                    #{n.community + 1}
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

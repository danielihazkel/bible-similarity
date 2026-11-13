import { useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router'
import { useNeighbourhood } from '../api/hooks'
import type { NeighbourEdge, NeighbourNode } from '../api/types'
import { Segmented } from '../components/Controls'
import { ErrorBox, Loading } from '../components/Status'
import { TableCsv } from '../components/TableCsv'
import { useLocale } from '../context/localeContext'
import { neighbourhoodLink, unitLink } from '../lib/links'
import { unitLabel } from '../lib/names'
import { usePanZoom } from '../lib/panZoom'
import { downloadSvg, standaloneSvg } from '../lib/svgExport'
import { useQueryParams } from '../lib/urlState'
import '../i18n/pages/neighbourhood'
import '../styles/pages/NeighbourhoodPage.css'

// the kinds an edge can have, in the order its colour is chosen (api/neighbourhood.KINDS)
const KINDS = ['citation', 'known', 'sequence', 'allusion', 'borrowing', 'echo', 'phrase', 'lexical', 'semantic', 'fused'] as const
const KS = [4, 6, 10]
const HOPS = [1, 2]
const W = 960
const H = 640
const ZOOM = 1.4

/** A unit's parallels two steps out, as a graph (DESIGN.md §11.1, D149): each node a passage, each
 * edge drawn in the colour of its first kind; a click puts a passage in the middle. */
export function NeighbourhoodPage() {
  const { unitId = '' } = useParams()
  const { m, locale } = useLocale()
  const t = m.nbh
  const [params, update] = useQueryParams()
  const kRaw = Number(params.get('k'))
  const k = KS.includes(kRaw) ? kRaw : undefined
  const hRaw = Number(params.get('hops'))
  const hops = HOPS.includes(hRaw) ? hRaw : undefined
  const off = new Set((params.get('off') ?? '').split(',').filter(Boolean))
  const res = useNeighbourhood(unitId, k, hops)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const label = unitLabel(d.unit, locale)
  const toggle = (kind: string) => {
    const next = new Set(off)
    if (next.has(kind)) next.delete(kind)
    else next.add(kind)
    update({ off: next.size ? [...next].join(',') : null })
  }
  // the settings carried when a passage is put in the middle
  const keep = new URLSearchParams([...params.entries()].filter(([key]) => ['k', 'hops', 'off'].includes(key)))
  const present = new Set(d.edges.flatMap((e) => e.kinds))
  return (
    <div className="page nbh-page">
      <p className="small">
        <Link to={unitLink(d.unit.unit_id)}>{t.open}</Link>
      </p>
      <h1>{t.title(label)}</h1>
      <p className="lede">{t.lede}</p>
      <div className="toolbar">
        <Segmented label={t.k} value={d.k} options={KS.map((v) => ({ value: v, label: String(v) }))} onChange={(v) => update({ k: String(v) })} />
        <Segmented label={t.hops} value={d.hops} options={HOPS.map((v) => ({ value: v, label: t.hopNames[v] }))} onChange={(v) => update({ hops: String(v) })} />
      </div>
      <fieldset className="nbh-kinds">
        <legend>{t.kindsLabel}</legend>
        {KINDS.filter((kind) => present.has(kind)).map((kind) => (
          <label key={kind} className="check">
            <input type="checkbox" checked={!off.has(kind)} onChange={() => toggle(kind)} />
            <span className={`nbh-swatch nbh-${kind}`} aria-hidden="true" />
            {t.kinds[kind]}
          </label>
        ))}
      </fieldset>
      <p className="muted small">{t.colourNote}</p>
      {d.truncated && <p className="status">{t.truncated(d.nodes.length)}</p>}
      {d.nodes.length < 2 ? (
        <p className="status">{t.none}</p>
      ) : (
        <>
          <Graph nodes={d.nodes} edges={d.edges} off={off} centre={d.unit.unit_id} keep={keep} title={t.title(label)} />
          <NodeTable nodes={d.nodes} edges={d.edges} centre={d.unit.unit_id} keep={keep} />
        </>
      )}
    </div>
  )
}

/** The edge's colour: its first kind not switched off (none: not drawn). */
const shownKind = (e: NeighbourEdge, off: Set<string>) => e.kinds.find((k) => !off.has(k))

function Graph({
  nodes,
  edges,
  off,
  centre,
  keep,
  title,
}: {
  nodes: NeighbourNode[]
  edges: NeighbourEdge[]
  off: Set<string>
  centre: string
  keep: URLSearchParams
  title: string
}) {
  const { m, locale } = useLocale()
  const t = m.nbh
  const ref = useRef<SVGSVGElement>(null)
  const [view, setView] = useState({ x: 0, y: 0, s: 1 })
  const at = useMemo(() => new Map(nodes.map((n) => [n.unit.unit_id, n])), [nodes])
  const px = (n: NeighbourNode) => n.x * W
  const py = (n: NeighbourNode) => n.y * H
  // CSS pixels to drawing units
  const unit = () => W / (ref.current?.getBoundingClientRect().width || W)
  const zoomAt = (f: number, cx: number, cy: number) =>
    setView((v) => {
      const s = Math.min(8, Math.max(0.5, v.s * f))
      const g = s / v.s
      return { s, x: cx - (cx - v.x) * g, y: cy - (cy - v.y) * g }
    })
  const { handlers, dragged } = usePanZoom(ref, {
    onPan: (dx, dy) => setView((v) => ({ ...v, x: v.x + dx * unit(), y: v.y + dy * unit() })),
    onZoom: (f, x, y) => zoomAt(f, x * unit(), y * unit()),
  })
  const save = () => {
    if (ref.current) downloadSvg('neighbourhood.svg', standaloneSvg(ref.current, title))
  }
  return (
    <>
      <div className="toolbar nbh-tools">
        <button type="button" onClick={() => zoomAt(ZOOM, W / 2, H / 2)}>
          {t.zoomIn}
        </button>
        <button type="button" onClick={() => zoomAt(1 / ZOOM, W / 2, H / 2)}>
          {t.zoomOut}
        </button>
        <button type="button" onClick={() => setView({ x: 0, y: 0, s: 1 })}>
          {t.reset}
        </button>
        <button type="button" onClick={save}>
          {t.svg}
        </button>
      </div>
      <svg ref={ref} className="nbh-graph" viewBox={`0 0 ${W} ${H}`} role="group" aria-label={t.graphLabel} direction="ltr" {...handlers}>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.s})`}>
          <g className="nbh-edges" aria-hidden="true">
            {edges.map((e) => {
              const a = at.get(e.a)
              const b = at.get(e.b)
              const kind = shownKind(e, off)
              if (!a || !b || !kind) return null
              return <line key={`${e.a}|${e.b}`} className={`nbh-edge nbh-${kind}`} x1={px(a)} y1={py(a)} x2={px(b)} y2={py(b)} strokeWidth={1.5 / view.s} />
            })}
          </g>
          {nodes.map((n) => {
            const id = n.unit.unit_id
            const label = unitLabel(n.unit, locale)
            const r = (n.hop === 0 ? 9 : n.hop === 1 ? 6 : 4) / Math.sqrt(view.s)
            return (
              // a router Link inside <svg> renders an SVG <a>; out of the tab order, the table below
              // has every passage
              <Link
                key={id}
                to={neighbourhoodLink(id, keep)}
                tabIndex={-1}
                aria-label={t.nodeTitle(label, n.hop)}
                onClick={(e) => {
                  if (dragged()) e.preventDefault()
                }}
              >
                <title>{t.nodeTitle(label, n.hop)}</title>
                <circle cx={px(n)} cy={py(n)} r={r} className={`nbh-node nbh-hop-${n.hop}${id === centre ? ' centre' : ''}`} />
                {n.hop < 2 && (
                  <text x={px(n) + r + 3} y={py(n) + 4} className="nbh-label" fontSize={12 / view.s}>
                    {label}
                  </text>
                )}
              </Link>
            )
          })}
        </g>
      </svg>
    </>
  )
}

/** Every passage drawn, with the kinds of its link to the middle: the graph as text. */
function NodeTable({ nodes, edges, centre, keep }: { nodes: NeighbourNode[]; edges: NeighbourEdge[]; centre: string; keep: URLSearchParams }) {
  const { m, locale } = useLocale()
  const t = m.nbh
  const toCentre = new Map(edges.filter((e) => e.a === centre || e.b === centre).map((e) => [e.a === centre ? e.b : e.a, e.kinds]))
  const rows = [...nodes].sort((a, b) => a.hop - b.hop || a.unit.start_verse_id - b.unit.start_verse_id)
  return (
    <section aria-labelledby="nbh-table">
      <h2 id="nbh-table">{t.tableTitle(nodes.length)}</h2>
      <TableCsv name="neighbourhood">
      <table className="data-table nbh-table">
        <thead>
          <tr>
            <th scope="col">{t.cols.passage}</th>
            <th scope="col" className="num">
              {t.cols.hop}
            </th>
            <th scope="col">{t.cols.kinds}</th>
            <th scope="col">{t.cols.centre}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((n) => {
            const id = n.unit.unit_id
            return (
              <tr key={id}>
                <td>
                  <Link to={unitLink(id)}>{unitLabel(n.unit, locale)}</Link>
                </td>
                <td className="num">{n.hop}</td>
                <td>{(toCentre.get(id) ?? []).map((k) => t.kinds[k]).join(' · ')}</td>
                <td>{id === centre ? t.centreIt : <Link to={neighbourhoodLink(id, keep)}>{t.cols.centre}</Link>}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      </TableCsv>
    </section>
  )
}

// The family tree itself: the zoomable drawing, its figures and the legend.
import { useEffect, useMemo, useRef, useState } from 'react'
import type { TreeNode } from '../../api/types'
import { Avatar } from '../../components/Avatar'
import {
  AVATAR,
  type FamilyIndex,
  HEADER_H,
  NODE_H,
  NODE_W,
  SPOUSES_SHOWN,
  shownAt,
  type TreeLayout,
} from '../../lib/familyTree'
import { usePanZoom } from '../../lib/panZoom'
import { Name } from './Name'
import { DOT_MIN, FIT_PAD, KEY_STEP, K_DOT, K_DOTS, K_MAX, K_MIN, K_SMALL, MARGIN, ZOOM } from './shared'
import type { Named, Namer, T } from './shared'

interface View {
  x: number
  y: number
  k: number
}

/** The part of the view the panel leaves free, in CSS pixels from the view's top left: beside a
 * card down one side, above a sheet along the bottom (a phone's). */
interface Free {
  x0: number
  x1: number
  y0: number
  y1: number
}

function freeOf(r: DOMRect, p: DOMRect | undefined): Free {
  const all = { x0: 0, x1: r.width, y0: 0, y1: r.height }
  if (!p || !p.width || !p.height) return all
  const ox = Math.min(r.right, p.right) - Math.max(r.left, p.left)
  const oy = Math.min(r.bottom, p.bottom) - Math.max(r.top, p.top)
  if (ox <= 0 || oy <= 0) return all
  if (oy > r.height / 2) return p.left - r.left > r.right - p.right ? { ...all, x1: p.left - r.left } : { ...all, x0: p.right - r.left }
  return { ...all, y1: p.top - r.top }
}

interface TreeProps {
  ix: FamilyIndex
  layout: TreeLayout
  name: Namer
  t: T
  num: (n: number) => string
  selected?: number
  line?: Set<number> // the selected person's line, from Adam down
  anchor?: number
  centre?: { id: number; seq: number }
  panel: React.RefObject<HTMLElement | null>
  stage: React.RefObject<HTMLDivElement | null>
  onSelect: (id: number) => void
  onToggle: (id: number) => void
}

interface FigureProps {
  x: number
  y: number
  sex: TreeNode['sex']
  kind: TreeNode['kind']
  cls: string
  name: Named
  current: boolean
  warn?: boolean
  sr?: string // said after the name to a screen reader
  onClick: () => void
  children?: React.ReactNode
}

/** One avatar with the name under it: a person, or a spouse drawn beside them. */
function Figure({ x, y, sex, kind, cls, name, current, warn, sr, onClick, children }: FigureProps) {
  return (
    <div className={cls} style={{ left: x - NODE_W / 2, top: y, width: NODE_W, height: NODE_H }}>
      <button type="button" className="gt-name" aria-current={current ? 'true' : undefined} onClick={onClick}>
        <span className="gt-avatar">
          <Avatar sex={sex} kind={kind} />
          {warn && (
            <span className="gt-badge" aria-hidden="true">
              ⚠
            </span>
          )}
        </span>
        <span className="gt-label">
          <Name n={name} />
        </span>
        {sr && <span className="sr-only">{sr}</span>}
      </button>
      {children}
    </div>
  )
}

/** The tree: an SVG layer of edges under HTML avatars and headers, panned and zoomed as one; only
 * what is in view (and a margin) is drawn, as dots when zoomed far out. */
export function TreeView({ ix, layout, name, t, num, selected, line, anchor, centre, panel, stage, onSelect, onToggle }: TreeProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 800, h: 560 })
  const [free, setFree] = useState<Free>()
  useEffect(() => {
    const el = ref.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const measure = () => {
      if (!el.clientWidth) return
      setSize((s) => (s.w === el.clientWidth && s.h === el.clientHeight ? s : { w: el.clientWidth, h: el.clientHeight }))
      const f = freeOf(el.getBoundingClientRect(), panel.current?.getBoundingClientRect())
      setFree((o) => (o && o.x0 === f.x0 && o.x1 === f.x1 && o.y0 === f.y0 && o.y1 === f.y1 ? o : f))
    }
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    if (panel.current) ro.observe(panel.current)
    return () => ro.disconnect()
  }, [panel])
  const fr = free ?? { x0: 0, x1: size.w, y0: 0, y1: size.h }
  const cx = (fr.x0 + fr.x1) / 2
  const cy = fr.y0 + (fr.y1 - fr.y0) / 3
  const top = layout.nodes.find((n) => n.node.placement === 'root') ?? layout.nodes[0]
  const home: View = { k: 1, x: cx - (top?.x ?? 0), y: 16 }
  const [stored, setView] = useState<View>()
  const [glide, setGlide] = useState(false) // the next move eases (a button's, not a drag's)
  const [auto, setAuto] = useState<number>() // the person last brought into view, until the reader moves
  const view = stored ?? home
  const spot = (id: number) => layout.at.get(id) ?? layout.spouseAt.get(id)
  const at = (v: View, id: number, x: number, y: number) => {
    setGlide(true)
    setAuto(id)
    setView({ k: v.k, x: cx - x * v.k, y: cy - y * v.k })
  }

  // a new layout keeps the node just opened or closed where it was on screen
  const [prev, setPrev] = useState(layout)
  if (prev !== layout) {
    setPrev(layout)
    const a = anchor === undefined ? undefined : prev.at.get(anchor)
    const b = anchor === undefined ? undefined : layout.at.get(anchor)
    if (a && b) {
      setGlide(false)
      setView({ ...view, x: view.x - (b.x - a.x) * view.k, y: view.y - (b.y - a.y) * view.k })
    }
  }
  // a person chosen outside the tree (search, the panel, the address) is brought into view
  const [done, setDone] = useState(0)
  if (centre && centre.seq !== done) {
    const c = spot(centre.id)
    if (c || shownAt(ix, centre.id) === undefined) setDone(centre.seq)
    if (c) at(view, centre.id, c.x, c.y + NODE_H / 2)
  }
  // the panel opened, closed or the view resized: bring that person back into the free part
  const freeKey = `${fr.x0} ${fr.x1} ${fr.y0} ${fr.y1}`
  const [seenFree, setSeenFree] = useState(freeKey)
  if (seenFree !== freeKey) {
    setSeenFree(freeKey)
    const id = auto ?? selected
    const c = id === undefined ? undefined : spot(id)
    if (c) {
      const sx = view.x + c.x * view.k
      const sy = view.y + (c.y + NODE_H / 2) * view.k
      if (auto !== undefined || sx < fr.x0 + NODE_W / 2 || sx > fr.x1 - NODE_W / 2 || sy > fr.y1) at(view, id!, c.x, c.y + NODE_H / 2)
    }
  }

  const zoomAt = (v: View, f: number, px: number, py: number): View => {
    const k = Math.min(K_MAX, Math.max(K_MIN, v.k * f))
    const r = k / v.k
    return { k, x: px - (px - v.x) * r, y: py - (py - v.y) * r }
  }
  /** A move of the reader's: eased for a button, at once for a drag or the wheel. */
  const move = (f: (v: View) => View, ease = false) => {
    setGlide(ease)
    setAuto(undefined)
    setView((v) => f(v ?? home))
  }
  const { handlers, dragged } = usePanZoom(ref, {
    wheel: 'zoom',
    onPan: (dx, dy) => move((v) => ({ ...v, x: v.x + dx, y: v.y + dy })),
    onZoom: (f, px, py) => move((v) => zoomAt(v, f, px, py)),
  })
  const zoom = (f: number) => move((v) => zoomAt(v, f, cx, cy), true)
  const fit = () =>
    move(() => {
      const k = Math.min(1, K_MAX, Math.max(K_MIN, Math.min((fr.x1 - fr.x0 - 2 * FIT_PAD) / layout.width, (fr.y1 - fr.y0 - 2 * FIT_PAD) / layout.height)))
      return { k, x: fr.x0 + (fr.x1 - fr.x0 - layout.width * k) / 2, y: fr.y0 + FIT_PAD }
    }, true)
  const goHome = () => {
    setGlide(true)
    setAuto(undefined)
    setView(undefined)
  }
  const onKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget) return
    const step = { ArrowLeft: [KEY_STEP, 0], ArrowRight: [-KEY_STEP, 0], ArrowUp: [0, KEY_STEP], ArrowDown: [0, -KEY_STEP] }[e.key]
    if (step) {
      e.preventDefault()
      move((v) => ({ ...v, x: v.x + step[0], y: v.y + step[1] }), true)
    } else if (e.key === '+' || e.key === '=') zoom(ZOOM)
    else if (e.key === '-') zoom(1 / ZOOM)
    else if (e.key === '0') fit()
    else if (e.key === 'Home') goHome()
  }
  const onDoubleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if ((e.target as Element).closest('button')) return
    const r = e.currentTarget.getBoundingClientRect()
    move((v) => zoomAt(v, e.shiftKey ? 1 / 2 : 2, e.clientX - r.left, e.clientY - r.top), true)
  }

  // full screen: the whole stage (the tree, the search, the card)
  const [full, setFull] = useState(false)
  useEffect(() => {
    const on = () => setFull(!!stage.current && document.fullscreenElement === stage.current)
    document.addEventListener('fullscreenchange', on)
    return () => document.removeEventListener('fullscreenchange', on)
  }, [stage])
  const canFull = typeof document !== 'undefined' && !!document.fullscreenEnabled
  const toggleFull = () => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void stage.current?.requestFullscreen()
  }
  const [legend, setLegend] = useState(false)

  // the selected person's line: its routes, and the mothers (or the spouse) on it
  // (a woman married twice is drawn beside each husband: a spouse is `host:id`)
  const lit = useMemo(() => {
    const paths: string[] = []
    const spouses = new Set<string>()
    const couple = (host: number | null | undefined, id: number | null) => {
      const h = host === null || host === undefined ? undefined : layout.at.get(host)
      const s = h?.spouses.find((x) => x.id === id)
      if (!h || !s) return
      paths.push(`M${h.x} ${h.y + AVATAR / 2}H${s.x}`)
      spouses.add(`${host}:${id}`)
    }
    for (const id of line ?? []) {
      const n = layout.at.get(id)
      if (!n) continue
      if (n.route) paths.push(n.route)
      if (n.node.role === 'father') couple(n.node.parent, n.node.mother)
    }
    if (selected !== undefined && !ix.byId.has(selected)) couple(ix.host.get(selected), selected)
    return { paths, spouses }
  }, [line, layout, selected, ix])

  // what is in view, in layout units
  const x0 = (-view.x - MARGIN) / view.k
  const x1 = (size.w - view.x + MARGIN) / view.k
  const y0 = (-view.y - MARGIN) / view.k
  const y1 = (size.h - view.y + MARGIN) / view.k
  const nodes = layout.nodes.filter((n) => {
    const xs = [n.x, ...n.spouses.map((s) => s.x)]
    return Math.max(...xs) + NODE_W / 2 >= x0 && Math.min(...xs) - NODE_W / 2 <= x1 && n.y + NODE_H >= y0 && n.y <= y1
  })
  const lod = view.k < K_DOTS ? 'dots' : view.k < K_SMALL ? 'small' : 'full'
  const headers = lod === 'dots' ? [] : layout.headers.filter((h) => h.x + NODE_W / 2 >= x0 && h.x - NODE_W / 2 <= x1 && h.y >= y0 && h.y <= y1)
  const edges = layout.edges.filter((e) => e.box[2] >= x0 && e.box[0] <= x1 && e.box[3] >= y0 && e.box[1] <= y1)
  const click = (f: () => void) => () => {
    if (!dragged()) f()
  }
  const isSel = (id: number) => id === selected
  const pct = `${num(Math.round(view.k * 100))}%`
  const dot = (key: string, id: number, x: number, y: number, sex: TreeNode['sex'], on: boolean) => (
    <circle
      key={key}
      className={`gt-dot sex-${sex ?? 'x'}${on ? ' on' : ''}${isSel(id) ? ' selected' : ''}`}
      cx={x}
      cy={y + AVATAR / 2}
      r={Math.max(AVATAR / 2, DOT_MIN / view.k)}
      onClick={click(() => move((v) => zoomAt(v, K_DOT / v.k, v.x + x * v.k, v.y + (y + AVATAR / 2) * v.k), true))}
    >
      <title>{t.dot(name(id).text)}</title>
    </circle>
  )

  return (
    <div className="gt-tree">
      {/* left to right inside in either language: the layout mirrors itself for Hebrew */}
      <div ref={ref} className="gt-viewport" dir="ltr" tabIndex={0} role="group" aria-label={t.treeLabel} onKeyDown={onKey} onDoubleClick={onDoubleClick} {...handlers}>
        <div
          className={`gt-canvas lod-${lod}${glide ? ' glide' : ''}`}
          style={{ width: layout.width, height: layout.height, transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}
        >
          <svg className="gt-edges" width={layout.width} height={layout.height} aria-hidden="true">
            {edges.map((e) => (
              <path key={e.key} className={e.cls} d={e.d} />
            ))}
            {lit.paths.map((d) => (
              <path key={d} className="gt-line-on" d={d} />
            ))}
            {lod === 'dots' && (
              <g className="gt-dots">
                {nodes.flatMap(({ node: n, x, y, spouses }) => [
                  dot(`n${n.person_id}`, n.person_id, x, y, n.sex, !!line?.has(n.person_id)),
                  ...spouses.map((s) => dot(`s${n.person_id}:${s.id}`, s.id, s.x, y, ix.spouse.get(s.id)?.sex ?? null, lit.spouses.has(`${n.person_id}:${s.id}`))),
                ])}
              </g>
            )}
          </svg>
          {headers.map((h) => {
            const label = typeof h.group === 'number' ? t.byMother(name(h.group).text) : h.group === 'none' ? t.motherUnnamed : t.attached(h.n)
            return (
              <div key={h.key} className={`gt-header ${typeof h.group === 'number' ? 'mother' : h.group}`} style={{ left: h.x - NODE_W / 2, top: h.y - HEADER_H / 2, width: NODE_W, height: HEADER_H }} title={label}>
                {typeof h.group === 'number' ? (
                  <button type="button" className="linkish" onClick={click(() => onSelect(h.group as number))} dir="auto">
                    {label}
                  </button>
                ) : (
                  <span dir="auto">{label}</span>
                )}
              </div>
            )
          })}
          {lod !== 'dots' &&
            nodes.flatMap(({ node: n, x, y, expanded, hidden, spouses }) => {
              const kids = ix.kids.get(n.person_id)?.length ?? 0
              const more = n.spouses.length - SPOUSES_SHOWN
              const cls = [
                'gt-node',
                `kind-${n.kind}`,
                `sex-${n.sex ?? 'x'}`,
                n.kind === 'virtual' ? '' : n.reviewed ? 'reviewed' : 'unreviewed',
                n.conflict ? 'conflict' : '',
                line?.has(n.person_id) ? 'on' : '',
                isSel(n.person_id) ? 'selected' : '',
              ]
              return [
                <Figure
                  key={n.person_id}
                  x={x}
                  y={y}
                  sex={n.sex}
                  kind={n.kind}
                  cls={cls.filter(Boolean).join(' ')}
                  name={name(n.person_id)}
                  current={isSel(n.person_id)}
                  warn={n.conflict}
                  sr={[n.conflict ? `, ${t.srConflict}` : '', n.kind !== 'virtual' && !n.reviewed ? `, ${t.srUnreviewed}` : ''].join('')}
                  onClick={click(() => onSelect(n.person_id))}
                >
                  {more > 0 && (
                    <button type="button" className="gt-sub linkish" onClick={click(() => onSelect(n.person_id))}>
                      {t.moreSpouses(more)}
                    </button>
                  )}
                  {kids > 0 && (
                    <button type="button" className="gt-toggle" aria-expanded={expanded} aria-label={expanded ? t.hide : t.show(hidden)} onClick={click(() => onToggle(n.person_id))}>
                      {expanded ? '−' : `+${num(hidden)}`}
                    </button>
                  )}
                </Figure>,
                ...spouses.map((s) => {
                  const p = ix.spouse.get(s.id)
                  const scls = ['gt-spouse', `kind-${p?.kind ?? 'person'}`, `sex-${p?.sex ?? 'x'}`, p?.reviewed ? 'reviewed' : 'unreviewed', lit.spouses.has(`${n.person_id}:${s.id}`) ? 'on' : '', isSel(s.id) ? 'selected' : '']
                  return (
                    <Figure
                      key={`s${n.person_id}:${s.id}`}
                      x={s.x}
                      y={y}
                      sex={p?.sex ?? null}
                      kind={p?.kind ?? 'person'}
                      cls={scls.filter(Boolean).join(' ')}
                      name={name(s.id)}
                      current={isSel(s.id)}
                      onClick={click(() => onSelect(s.id))}
                    />
                  )
                }),
              ]
            })}
        </div>
      </div>
      <div className="gt-tools" role="group" aria-label={t.zoom}>
        <button type="button" onClick={() => zoom(ZOOM)} aria-label={t.zoomIn} title={t.zoomIn}>
          +
        </button>
        <button type="button" onClick={() => zoom(1 / ZOOM)} aria-label={t.zoomOut} title={t.zoomOut}>
          −
        </button>
        <button type="button" className="gt-pct" onClick={() => move((v) => zoomAt(v, 1 / v.k, cx, cy), true)} aria-label={t.zoomLevel(pct)} title={t.zoomLevel(pct)}>
          {pct}
        </button>
        <button type="button" onClick={fit} aria-label={t.fit} title={t.fit}>
          ⤢
        </button>
        <button type="button" onClick={goHome} aria-label={t.home} title={t.home}>
          ⌂
        </button>
        {canFull && (
          <button type="button" onClick={toggleFull} aria-label={full ? t.exitFullscreen : t.fullscreen} title={full ? t.exitFullscreen : t.fullscreen} aria-pressed={full}>
            ⛶
          </button>
        )}
        <button type="button" className="gt-legend-toggle" aria-expanded={legend} onClick={() => setLegend((x) => !x)}>
          {t.legend}
        </button>
      </div>
      {legend && <Legend t={t} />}
    </div>
  )
}

function Legend({ t }: { t: T }) {
  const line = (cls: string) => (
    <svg className="gt-key-line" width="30" height="10" aria-hidden="true">
      <path className={cls} d="M1 5H29" />
    </svg>
  )
  const avatar = (sex: TreeNode['sex'], kind: TreeNode['kind'], cls = '') => (
    <span className={`gt-key-avatar ${cls}`} aria-hidden="true">
      <Avatar sex={sex} kind={kind} />
    </span>
  )
  return (
    <ul className="gt-legend small" aria-label={t.legend}>
      <li>
        {avatar('m', 'person')} {t.keys.man}
      </li>
      <li>
        {avatar('f', 'person')} {t.keys.woman}
      </li>
      <li>
        {avatar(null, 'group')} {t.keys.group}
      </li>
      <li>
        {line('gt-couple')} {t.keys.couple}
      </li>
      <li>
        {avatar('m', 'person', 'on')} {t.keys.line}
      </li>
      <li>
        {avatar('m', 'person', 'unreviewed')} {t.keys.unreviewed}
      </li>
      <li>
        {avatar('m', 'person', 'conflict')} {t.keys.conflict}
      </li>
      <li>
        {line('gt-edge desc')} {t.keys.desc}
      </li>
      <li>
        {line('gt-edge unstated')} {t.keys.unstated}
      </li>
      <li>
        {line('gt-cross')} {t.keys.cross}
      </li>
      <li>
        <span className="gt-key-header" aria-hidden="true" /> {t.keys.header}
      </li>
    </ul>
  )
}

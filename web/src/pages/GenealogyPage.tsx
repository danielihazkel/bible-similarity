import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useBooks, useGenealogyPerson, useGenealogySkeleton, usePersonLookup } from '../api/hooks'
import type { FamilyLink, PersonMatch, ProofVerse, TreeNode } from '../api/types'
import { Avatar } from '../components/Avatar'
import { HebrewText } from '../components/HebrewText'
import { ErrorBox, Loading } from '../components/Status'
import { useLocale } from '../context/localeContext'
import type { Messages } from '../i18n'
import {
  AVATAR,
  below,
  type FamilyIndex,
  HEADER_H,
  indexTree,
  layoutTree,
  NODE_H,
  NODE_W,
  opening,
  pathTo,
  SPOUSES_SHOWN,
  shownAt,
  type TreeLayout,
} from '../lib/familyTree'
import type { Highlight } from '../lib/highlight'
import { unitLink } from '../lib/links'
import { bookName } from '../lib/names'
import { usePanZoom } from '../lib/panZoom'
import { personAbout } from '../lib/people'
import { useQueryParams } from '../lib/urlState'

const OPEN_GENERATIONS = 3 // the tree opens with Adam's first generations expanded
const K_MIN = 0.02 // zoom limits (at the least, the whole tree opened)
const K_MAX = 3
const K_SMALL = 0.45 // below this zoom, names only: no lines under them, no open / close buttons
const K_DOTS = 0.22 // ... and below this, each person a dot
const K_DOT = 0.9 // the zoom a click on a dot goes to
const DOT_MIN = 2.5 // CSS pixels a dot keeps on screen however far out
const ZOOM = 1.4 // a step of the + / − buttons and keys
const KEY_STEP = 80 // CSS pixels an arrow key moves the tree
const MARGIN = 160 // CSS pixels beyond the view still drawn
const FIT_PAD = 24 // CSS pixels around the tree fitted into view
const MEMBERS_SHOWN = 40 // people attached to a node listed before "show all"

type T = Messages['gt']
type Named = { text: string; he: boolean }
type Namer = (id: number) => Named

/** A person's name as the tree writes it: the Hebrew name; for the unnamed, what they are to the
 * one they are drawn under or beside ("בת לוט"); for the "unattached" groups, the book. */
function namer(ix: FamilyIndex, t: T, books: Map<number, string>): Namer {
  return (id) => {
    const n = ix.byId.get(id)
    const p = n ?? ix.spouse.get(id)
    if (!p) return { text: '', he: false }
    if (p.he) return { text: p.he, he: true }
    if (n?.kind === 'virtual') return { text: n.book_id === null ? t.unattached : (books.get(n.book_id) ?? String(n.book_id)), he: false }
    const of = n && n.parent !== null && n.role !== 'unstated' ? ix.byId.get(n.parent) : undefined
    if (of?.he) return { text: n!.sex === 'f' ? t.daughterOf(of.he) : n!.sex === 'm' ? t.sonOf(of.he) : t.childOf(of.he), he: false }
    const host = ix.host.get(id)
    const h = host === undefined ? '' : (ix.byId.get(host)?.he ?? '')
    if (h) return { text: p.sex === 'm' ? t.husbandOf(h) : t.wifeOf(h), he: false }
    return { text: t.unnamed(p.sex), he: false }
  }
}

function Name({ n }: { n: Named }) {
  return n.he ? (
    <span lang="he" dir="rtl" className="he">
      {n.text}
    </span>
  ) : (
    <bdi>{n.text}</bdi>
  )
}

/** Overview → Family tree (§16.63, D103): everyone the text names, from Adam down, collapsible at
 * any node, on most of the screen; a person (`?p=`) opens the line down to them, lights it, and
 * opens a card over the tree with their family and the verses that state each link. */
export function GenealogyPage() {
  const { m, locale } = useLocale()
  const t = m.gt
  const [params, update] = useQueryParams()
  const pv = params.get('p')
  const selected = pv && Number.isFinite(Number(pv)) ? Number(pv) : undefined
  const sk = useGenealogySkeleton()
  const books = useBooks()
  const ix = useMemo(() => (sk.data ? indexTree(sk.data) : undefined), [sk.data])
  const bookNames = useMemo(() => new Map((books.data ?? []).map((b) => [b.book_id, bookName(b, locale)])), [books.data, locale])
  const name = useMemo(() => (ix ? namer(ix, t, bookNames) : undefined), [ix, t, bookNames])
  const [expanded, setExpanded] = useState<Set<number>>()
  const [anchor, setAnchor] = useState<number>() // the node kept in place when the layout changes
  const [centre, setCentre] = useState<{ id: number; seq: number }>()
  const [opened, setOpened] = useState<number>() // the selected person whose line is open
  const [quiet, setQuiet] = useState<number>() // chosen in the tree: already in view
  const panel = useRef<HTMLElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  if (ix && !expanded) setExpanded(opening(ix, OPEN_GENERATIONS))
  if (ix && expanded && selected !== undefined && opened !== selected) {
    setOpened(selected)
    const closed = pathTo(ix, selected)
      .slice(0, -1)
      .filter((id) => !expanded.has(id))
    if (closed.length) setExpanded(new Set([...expanded, ...closed]))
    if (quiet !== selected) setCentre({ id: selected, seq: (centre?.seq ?? 0) + 1 })
  }
  const layout = useMemo(() => (ix && expanded && sk.data ? layoutTree(ix, expanded, sk.data.cross, locale === 'he') : undefined), [ix, expanded, sk.data, locale])
  const line = useMemo(() => (ix && selected !== undefined ? new Set(pathTo(ix, selected)) : undefined), [ix, selected])

  const show = (id: number) => setCentre({ id, seq: (centre?.seq ?? 0) + 1 })
  const pick = (id: number) => {
    setQuiet(undefined)
    if (id === selected) show(id)
    else update({ p: String(id) }, false)
  }
  const choose = (id: number) => {
    setQuiet(id)
    update({ p: String(id) }, false)
  }
  const toggle = (id: number) => {
    setAnchor(id)
    setExpanded((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const openAll = (id: number, open: boolean) => {
    if (!ix) return
    const at = shownAt(ix, id)
    if (at === undefined) return
    setAnchor(at)
    setExpanded((s) => {
      const next = new Set(s)
      for (const x of [at, ...below(ix, at)]) {
        if (open) next.add(x)
        else next.delete(x)
      }
      return next
    })
  }
  const meta = sk.data?.meta
  const ready = !!(sk.data?.nodes.length && ix && name && layout)

  return (
    <div className="page genealogy-page">
      <div className="gt-head">
        <h1>{t.title}</h1>
        {ready && <p className="muted small">{t.summary(meta?.persons ?? 0, meta?.parent_links ?? 0, meta?.proved ?? 0, meta?.reviewed_links ?? 0)}</p>}
        <details className="gt-about">
          <summary className="small">{t.about}</summary>
          <p className="lede">{t.lede}</p>
        </details>
      </div>
      {sk.isPending ? (
        <Loading />
      ) : sk.error ? (
        <ErrorBox error={sk.error} />
      ) : !ready ? (
        <p className="status">{t.noData}</p>
      ) : (
        <div ref={stage} className="gt-stage">
          <TreeView
            ix={ix!}
            layout={layout!}
            name={name!}
            t={t}
            num={m.num}
            selected={selected}
            line={line}
            anchor={anchor}
            centre={centre}
            panel={panel}
            stage={stage}
            onSelect={choose}
            onToggle={toggle}
          />
          <PersonSearch t={t} onPick={pick} />
          {selected === undefined && <p className="gt-idle muted small">{t.idle}</p>}
          <aside ref={panel} className={`gt-side${selected !== undefined ? ' open' : ''}`} onKeyDown={(e) => e.key === 'Escape' && update({ p: null })}>
            {selected !== undefined && (
              <GenealogyPanel
                personId={selected}
                ix={ix!}
                name={name!}
                t={t}
                onPick={pick}
                onShow={show}
                onOpenAll={openAll}
                onClose={() => update({ p: null })}
              />
            )}
          </aside>
        </div>
      )}
    </div>
  )
}

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
function TreeView({ ix, layout, name, t, num, selected, line, anchor, centre, panel, stage, onSelect, onToggle }: TreeProps) {
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

function PersonSearch({ t, onPick }: { t: T; onPick: (id: number) => void }) {
  const { locale } = useLocale()
  const [q, setQ] = useState('')
  const dq = useDeferredValue(q.trim())
  const res = usePersonLookup(dq)
  const items = q.trim() && res.data?.query === dq ? res.data.items : undefined
  const choose = (x: PersonMatch) => {
    setQ('')
    onPick(x.person_id)
  }
  return (
    <div className="gt-search">
      <label className="control">
        <span>{t.search}</span>
        <input
          type="search"
          value={q}
          placeholder={t.searchHint}
          lang="he"
          dir="rtl"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && items?.length) choose(items[0])
            else if (e.key === 'Escape') setQ('')
          }}
        />
      </label>
      {items &&
        (items.length ? (
          <ul className="gt-matches" aria-label={t.matches}>
            {items.map((x) => (
              <li key={x.person_id}>
                <button type="button" className="linkish" onClick={() => choose(x)}>
                  <span lang="he" dir="rtl" className="he">
                    {x.he}
                  </span>
                </button>{' '}
                <span className="muted small" dir="auto">
                  {personAbout(x, t, locale)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted small">{t.noMatch(q.trim())}</p>
        ))}
    </div>
  )
}

interface PanelProps {
  personId: number
  ix: FamilyIndex
  name: Namer
  t: T
  onPick: (id: number) => void
  onShow: (id: number) => void
  onOpenAll: (id: number, open: boolean) => void
  onClose: () => void
}

/** One person: where they stand, their family with the verses of each link, the readings where
 * the text disagrees. */
function GenealogyPanel({ personId, ix, name, t, onPick, onShow, onOpenAll, onClose }: PanelProps) {
  const { locale } = useLocale()
  const res = useGenealogyPerson(personId)
  const [allMembers, setAllMembers] = useState(false)
  if (res.isPending) return <Loading />
  if (res.error) return <ErrorBox error={res.error} />
  const d = res.data
  const p = d.person
  const host = ix.host.get(p.person_id)
  const tribe = d.attached && p.placement === 'tribe' ? name(d.attached.person.person_id) : undefined
  const below_ = ix.kids.get(p.person_id)?.length ?? 0
  const first = locale === 'he' ? d.first_label_he : d.first_label
  const who = (id: number) => (
    <button type="button" className="linkish" onClick={() => onPick(id)}>
      <Name n={name(id)} />
    </button>
  )
  const links = (ls: FamilyLink[], compact = false, roles = true) => (
    <ul className="gt-links">
      {ls.map((l) => (
        <LinkItem key={l.link_id} l={l} t={t} who={who} compact={compact} role={roles} />
      ))}
    </ul>
  )
  const members = allMembers ? d.members : d.members.slice(0, MEMBERS_SHOWN)
  return (
    <section className="gt-panel" aria-label={t.panel}>
      <div className="word-head">
        <h2>
          <Name n={name(p.person_id)} /> {p.kind !== 'person' && <span className={`type-tag gt-kind-${p.kind}`}>{t.kinds[p.kind as keyof T['kinds']]}</span>}
        </h2>
        <button type="button" className="linkish" onClick={onClose}>
          {t.close}
        </button>
      </div>
      {p.kind !== 'virtual' && (
        <p className="muted small">
          {first && p.first_vid !== null && (
            <>
              {t.firstNamed} <Link to={unitLink(`v:${p.first_vid}`)}>{first}</Link> ·{' '}
            </>
          )}
          {t.verseCount(p.n_verses)} · {p.reviewed ? t.reviewed : t.notReviewed}
        </p>
      )}
      {tribe && <p className="small">{t.placedTribe(tribe.text)}</p>}
      {p.placement === 'unattached' && <p className="small">{t.placedUnattached}</p>}
      {p.placement === 'spouse' && host !== undefined && <p className="small">{t.placedSpouse(name(host).text)}</p>}
      <p className="gt-actions">
        <button type="button" onClick={() => onShow(p.person_id)}>
          {t.showInTree}
        </button>
        {below_ > 0 && (
          <>
            <button type="button" onClick={() => onOpenAll(p.person_id, true)}>
              {t.openAll}
            </button>
            <button type="button" onClick={() => onOpenAll(p.person_id, false)}>
              {t.closeAll}
            </button>
          </>
        )}
      </p>
      {d.conflicts.length > 0 && (
        <section className="gt-conflicts">
          <h3>
            <span className="gt-warn" aria-hidden="true">
              ⚠
            </span>{' '}
            {t.conflicts}
          </h3>
          {d.conflicts.map((c) => (
            <div key={c.conflict_id} className="gt-conflict">
              <p className="small">
                <strong>{t.conflictKinds[c.kind]}</strong>
                {(locale === 'he' ? c.note_he : c.note_en) && ` · ${locale === 'he' ? c.note_he : c.note_en}`}
              </p>
              <ul className="gt-links">
                {c.readings.map((l, i) => (
                  <LinkItem key={l.link_id} l={l} t={t} who={who} reading={i === 0 ? t.readingDrawn : t.readingOther} />
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}
      {d.identities.length > 0 && (
        <section className="gt-identities">
          <h3>{t.identities}</h3>
          {d.identities.map((x) => {
            const note = locale === 'he' ? x.note_he : x.note_en
            return (
              <div key={x.identity_id} className="gt-identity">
                <p className="small">
                  {x.person ? (
                    <>
                      {t.maybeSame} {who(x.person.person_id)}
                    </>
                  ) : (
                    t.mergedFrom(x.n_keys)
                  )}
                  {note && ` · ${note}`}
                </p>
                <ol className="gt-proofs">
                  {x.proofs.map((v) => (
                    <Proof key={v.verse.verse_id} v={v} t={t} />
                  ))}
                </ol>
              </div>
            )
          })}
        </section>
      )}
      {d.parents.length > 0 && (
        <>
          <h3>{t.parents}</h3>
          {links(d.parents)}
        </>
      )}
      {d.spouses.length > 0 && (
        <>
          <h3>{t.spouses}</h3>
          {links(d.spouses, false, false)}
        </>
      )}
      {d.children.length > 0 && (
        <>
          <h3>{t.children}</h3>
          {d.children.map((g) => (
            <div key={g.adopted ? 'adopted' : (g.other?.person_id ?? 0)} className="gt-child-group">
              <h4 className="small">
                {g.adopted ? (
                  t.childrenAdopted
                ) : g.other ? (
                  <>
                    {g.other.sex === 'f' ? t.childrenBy : t.childrenOf} {who(g.other.person_id)}
                  </>
                ) : (
                  t.childrenUnnamed
                )}
              </h4>
              {links(g.children, true, false)}
            </div>
          ))}
        </>
      )}
      {d.siblings.length > 0 && (
        <>
          <h3>{t.siblings}</h3>
          <p className="gt-names">
            {d.siblings.map((s) => (
              <span key={s.person_id}>{who(s.person_id)}</span>
            ))}
          </p>
        </>
      )}
      {d.members.length > 0 && (
        <>
          <h3>{t.members(d.members.length)}</h3>
          <p className="muted small">{t.membersLede}</p>
          <p className="gt-names">
            {members.map((s) => (
              <span key={s.person_id}>{who(s.person_id)}</span>
            ))}
          </p>
          {d.members.length > MEMBERS_SHOWN && (
            <button type="button" className="linkish" onClick={() => setAllMembers((x) => !x)}>
              {allMembers ? t.showFewer : t.showAll(d.members.length)}
            </button>
          )}
        </>
      )}
    </section>
  )
}

interface LinkProps {
  l: FamilyLink
  t: T
  who: (id: number) => React.ReactNode
  compact?: boolean // the verses folded (a child's)
  role?: boolean // say father / mother
  reading?: string // a conflict's reading: which
}

function LinkItem({ l, t, who, compact = false, role = true, reading }: LinkProps) {
  const tags = [
    role && !reading ? t.roles[l.role] : undefined,
    reading,
    l.kind === 'descendant' ? t.descendant : undefined,
    l.kind === 'adopted' ? t.adopted : undefined,
    t.status[l.status],
    l.marker && t.markers[l.marker] ? t.markers[l.marker] : undefined,
    l.doubt ? t.doubt : undefined,
    (l.role === 'father' || l.role === 'mother') && !reading ? (l.drawn ? t.drawn : t.notDrawn) : undefined,
  ].filter(Boolean)
  const proved = l.proofs.filter((v) => v.cue !== 'nearby')
  const hint = l.proofs.filter((v) => v.cue === 'nearby')
  const verses = (
    <>
      {!proved.length && l.role !== 'unstated' && <p className="muted small">{t.noProof}</p>}
      {hint.length > 0 && <p className="muted small">{t.nearbyHint}</p>}
      <ol className="gt-proofs">
        {l.proofs.map((v) => (
          <Proof key={v.verse.verse_id} v={v} t={t} />
        ))}
      </ol>
    </>
  )
  return (
    <li className={`gt-link${l.kind === 'descendant' ? ' desc' : ''}${l.status === 'tipnr' ? ' unreviewed' : ''}`}>
      <span className="gt-link-head">
        {who(l.person.person_id)}{' '}
        {tags.map((x) => (
          <span key={x} className="gt-tag small">
            {x}
          </span>
        ))}
      </span>
      {compact ? (
        <details>
          <summary className="small">{l.proofs.length ? t.verses(proved.length || l.proofs.length) : t.noProof}</summary>
          {verses}
        </details>
      ) : (
        verses
      )}
    </li>
  )
}

function Proof({ v, t }: { v: ProofVerse; t: T }) {
  const { locale } = useLocale()
  const hl: Highlight = new Map(v.tokens.map((i) => [i, 'focus']))
  return (
    <li className="hit gt-proof">
      <Link className="verse-ref" to={unitLink(`v:${v.verse.verse_id}`)}>
        {locale === 'he' ? v.verse.ref_he : v.verse.ref}
      </Link>{' '}
      {v.cue && (
        <span className="type-tag gt-cue" title={t.cueTitle}>
          {t.cues[v.cue]}
        </span>
      )}{' '}
      {v.source === 'curated' && <span className="muted small">{t.curated}</span>}
      <p className="hit-text">
        <HebrewText verse={v.verse} highlight={hl} />
      </p>
    </li>
  )
}

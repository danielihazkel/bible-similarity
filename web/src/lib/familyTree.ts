// The family tree's layout (DESIGN.md §16.63, D103): the drawn tree indexed once, then laid out by
// d3-hierarchy over the expanded part only. A person and the spouses drawn beside them are one
// unit, as wide as its avatars. Every expanded person's children hang from a header row: one
// header per mother when the children have more than one (the attached, by a link not stated,
// apart), else an unseen one; a mother drawn beside her husband needs no header, her children hang
// from the line between them. So each generation is two levels of the hierarchy and the
// generations line up across the tree.

import { hierarchy, tree } from 'd3-hierarchy'
import type { CrossLink, SkeletonResponse, TreeNode, TreeSpouse } from '../api/types'

export const NODE_W = 108 // a person's width (their avatar and name), CSS pixels
export const NODE_H = 84 // ... its height (the avatar, a name and a line under it)
export const AVATAR = 44 // the avatar's diameter, at the top of a person
export const COUPLE = NODE_W + 16 // between a person's avatar and a spouse's beside them
export const SPOUSES_SHOWN = 2 // spouses drawn beside a person (one on each side); the rest a count
export const GAP = 12 // between two siblings' units
export const GAP_COUSINS = 40 // ... between two units of different parents
export const ROW = 180 // the distance between generations
export const HEADER_H = 22 // a mother header's height
export const HEADER_Y = NODE_H + 40 // its middle, below its parent's top (under the open / close button)
export const BUS_Y = HEADER_Y + 24 // the line the children's drops start from
export const PAD = 24 // around the drawing

export interface FamilyIndex {
  byId: Map<number, TreeNode>
  kids: Map<number, TreeNode[]> // drawn children: TIPNR's order, then those attached
  spouse: Map<number, TreeSpouse> // the people drawn beside a spouse
  host: Map<number, number> // ... and the node each is drawn beside
  size: Map<number, number> // descendants drawn below a node
  roots: TreeNode[] // Adam, then "unattached"
}

export function indexTree(s: SkeletonResponse): FamilyIndex {
  const byId = new Map(s.nodes.map((n) => [n.person_id, n]))
  const kids = new Map<number, TreeNode[]>()
  const roots: TreeNode[] = []
  for (const n of s.nodes) {
    if (n.parent === null || !byId.has(n.parent)) roots.push(n)
    else kids.set(n.parent, [...(kids.get(n.parent) ?? []), n])
  }
  for (const list of kids.values()) list.sort((a, b) => (a.seq ?? Infinity) - (b.seq ?? Infinity) || a.person_id - b.person_id)
  roots.sort((a, b) => (a.placement === 'root' ? 0 : 1) - (b.placement === 'root' ? 0 : 1) || a.person_id - b.person_id)
  const spouse = new Map(s.spouses.map((x) => [x.person_id, x]))
  const host = new Map<number, number>()
  for (const n of s.nodes) for (const x of n.spouses) if (!host.has(x)) host.set(x, n.person_id)
  // descendants per node, children before parents
  const size = new Map<number, number>()
  const order: number[] = []
  const stack = roots.map((r) => r.person_id)
  while (stack.length) {
    const id = stack.pop()!
    order.push(id)
    for (const k of kids.get(id) ?? []) stack.push(k.person_id)
  }
  for (const id of order.reverse()) size.set(id, (kids.get(id) ?? []).reduce((t, k) => t + 1 + (size.get(k.person_id) ?? 0), 0))
  return { byId, kids, spouse, host, size, roots }
}

/** The drawn line from a root down to a person (a spouse: to the one beside it), both ends in. */
export function pathTo(ix: FamilyIndex, id: number): number[] {
  let at: number | undefined = ix.byId.has(id) ? id : ix.host.get(id)
  const path: number[] = []
  const seen = new Set<number>()
  while (at !== undefined && !seen.has(at)) {
    seen.add(at)
    path.unshift(at)
    const p = ix.byId.get(at)?.parent
    at = p === null || p === undefined ? undefined : p
  }
  return path
}

/** The node a person is shown at: itself, or the spouse it is drawn beside. */
export const shownAt = (ix: FamilyIndex, id: number) => (ix.byId.has(id) ? id : ix.host.get(id))

/** Every node below one (for "open all below"). */
export function below(ix: FamilyIndex, id: number): number[] {
  const out: number[] = []
  const stack = [id]
  while (stack.length) {
    const at = stack.pop()!
    for (const k of ix.kids.get(at) ?? []) {
      out.push(k.person_id)
      stack.push(k.person_id)
    }
  }
  return out
}

/** The nodes of the first generations under the root(s): the tree as it opens. */
export function opening(ix: FamilyIndex, generations: number): Set<number> {
  const out = new Set<number>()
  let level = ix.roots.filter((r) => r.placement === 'root')
  for (let g = 0; g < generations && level.length; g++) {
    for (const n of level) out.add(n.person_id)
    level = level.flatMap((n) => ix.kids.get(n.person_id) ?? [])
  }
  return out
}

export type GroupKey = number | 'none' | 'attached'

/** A person's children by mother (in the order of each's first child): those of an unnamed
 * mother as 'none', those attached by a link not stated as 'attached', last. */
export function childGroups(kids: TreeNode[]): { key: GroupKey; kids: TreeNode[] }[] {
  const out = new Map<GroupKey, TreeNode[]>()
  for (const k of kids) {
    const g: GroupKey = k.role === 'unstated' ? 'attached' : k.role === 'father' && k.mother !== null ? k.mother : 'none'
    out.set(g, [...(out.get(g) ?? []), k])
  }
  return [...out.entries()]
    .sort(([a], [b]) => (a === 'attached' ? 1 : 0) - (b === 'attached' ? 1 : 0))
    .map(([key, kids]) => ({ key, kids }))
}

export interface LaidNode {
  node: TreeNode
  x: number // its avatar's centre
  y: number // its top
  expanded: boolean
  hidden: number // descendants not drawn (collapsed)
  spouses: { id: number; x: number }[] // those drawn beside, their avatars' centres
  route?: string // the line down to it from its parent (or from the parent and its mother)
}
export interface LaidSpouse {
  x: number
  y: number
  host: number // the person drawn beside
}
export interface LaidHeader {
  key: string
  parent: number
  group: GroupKey
  n: number // its children
  x: number // its centre
  y: number // its middle
}
export interface LaidEdge {
  key: string
  d: string
  cls: string
  box: [number, number, number, number] // x0, y0, x1, y1
}
export interface TreeLayout {
  nodes: LaidNode[]
  headers: LaidHeader[]
  edges: LaidEdge[]
  width: number
  height: number
  at: Map<number, LaidNode>
  spouseAt: Map<number, LaidSpouse>
}

interface H {
  key: string
  node?: TreeNode
  group?: { key: GroupKey; parent: number; visible: boolean; n: number }
  children?: H[]
}

/** The edge class of the link a child hangs by: a descendant, a link not stated or a son. */
export const edgeClass = (n: TreeNode) => (n.role === 'unstated' ? 'gt-edge unstated' : n.link_kind === 'descendant' ? 'gt-edge desc' : 'gt-edge')

/** The spouses drawn beside a person: the first on the side of the first-born (so her children
 * hang below her without crossing another's line), the second on the other side. */
export const besides = (n: TreeNode) => n.spouses.slice(0, SPOUSES_SHOWN)

/** Half a unit's width: a person with the spouses beside them. */
const halfUnit = (n: TreeNode) => [0, COUPLE / 2, COUPLE][besides(n).length] + NODE_W / 2

function segment(key: string, cls: string, x0: number, y0: number, x1: number, y1: number): LaidEdge {
  return { key, cls, d: `M${x0} ${y0}L${x1} ${y1}`, box: [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)] }
}

/** The expanded part laid out: avatar centres and tops (a person's, their spouses'), headers,
 * edges (as segments, each with its box, to draw only those in view), the line down to each
 * person and cross-links between nodes both drawn; mirrored for a right-to-left page (the
 * first-born on the right, and a first wife on that side of her husband). */
export function layoutTree(ix: FamilyIndex, expanded: Set<number>, cross: CrossLink[], rtl: boolean): TreeLayout {
  const build = (n: TreeNode): H => {
    const kids = ix.kids.get(n.person_id) ?? []
    if (!expanded.has(n.person_id) || !kids.length) return { key: `n${n.person_id}`, node: n }
    const groups = childGroups(kids)
    return {
      key: `n${n.person_id}`,
      node: n,
      children: groups.map((g) => ({
        key: `h${n.person_id}:${g.key}`,
        group: {
          key: g.key,
          parent: n.person_id,
          visible: groups.length > 1 && !(typeof g.key === 'number' && besides(n).includes(g.key)),
          n: g.kids.length,
        },
        children: g.kids.map(build),
      })),
    }
  }
  const root = hierarchy<H>({ key: 'top', children: ix.roots.map(build) })
  const half = (h: H) => (h.node ? halfUnit(h.node) : NODE_W / 2)
  const laid = tree<H>()
    .nodeSize([1, 1])
    .separation((a, b) => half(a.data) + half(b.data) + (a.parent === b.parent ? GAP : GAP_COUSINS))(root)
  const all = laid.descendants().filter((d) => d.depth > 0)
  let lo = Infinity
  let hi = -Infinity
  for (const d of all) {
    lo = Math.min(lo, d.x - half(d.data))
    hi = Math.max(hi, d.x + half(d.data))
  }
  const X = (x: number) => (rtl ? hi - x : x - lo) + PAD
  // depth 1, 3, 5, ... are people (generation (depth - 1) / 2); 2, 4, ... their headers
  const top = (depth: number) => PAD + ((depth - 1) / 2) * ROW

  const nodes: LaidNode[] = []
  const headers: LaidHeader[] = []
  const edges: LaidEdge[] = []
  const at = new Map<number, LaidNode>()
  const spouseAt = new Map<number, LaidSpouse>()
  for (const d of all) {
    const n = d.data.node
    if (!n) continue
    // a unit's avatars, before mirroring: [first spouse] person [second spouse]
    const s = besides(n)
    const px = d.x + (s.length === 1 ? COUPLE / 2 : 0)
    const y = top(d.depth)
    const spouses = s.map((id, i) => ({ id, x: X(i === 0 ? px - COUPLE : px + COUPLE) }))
    const ln: LaidNode = { node: n, x: X(px), y, expanded: !!d.children, hidden: d.children ? 0 : (ix.size.get(n.person_id) ?? 0), spouses }
    nodes.push(ln)
    at.set(n.person_id, ln)
    for (const sp of spouses) {
      // drawn beside two husbands: where the index puts her (`host`), else wherever she is drawn
      if (ix.host.get(sp.id) === n.person_id || !spouseAt.has(sp.id)) spouseAt.set(sp.id, { x: sp.x, y, host: n.person_id })
      const [a, b] = sp.x > ln.x ? [ln.x + AVATAR / 2, sp.x - AVATAR / 2] : [sp.x + AVATAR / 2, ln.x - AVATAR / 2]
      edges.push(segment(`s${n.person_id}:${sp.id}`, 'gt-couple', a, y + AVATAR / 2, b, y + AVATAR / 2))
    }
  }
  const trunks = new Set<string>()
  for (const d of all) {
    if (d.data.node) continue
    const g = d.data.group!
    const p = at.get(g.parent)!
    const beside = typeof g.key === 'number' ? p.spouses.find((sp) => sp.id === g.key) : undefined
    // a mother beside: from the middle of the line between them; else from under the parent
    const [sx, sy] = beside ? [(p.x + beside.x) / 2, p.y + AVATAR / 2] : [p.x, p.y + NODE_H]
    const hx = X(d.x)
    const hy = p.y + HEADER_Y
    const bus = p.y + BUS_Y
    // the trunk, out to the header, down to the bus, along it and down to each child
    const tk = `t${g.parent}:${beside ? beside.id : 'p'}`
    if (!trunks.has(tk)) {
      trunks.add(tk)
      edges.push(segment(tk, 'gt-edge', sx, sy, sx, hy))
    }
    if (hx !== sx) edges.push(segment(`a${d.data.key}`, 'gt-edge', sx, hy, hx, hy))
    edges.push(segment(`b${d.data.key}`, 'gt-edge', hx, hy, hx, bus))
    const kids = (d.children ?? []).map((c) => at.get(c.data.node!.person_id)!)
    const xs = kids.map((c) => c.x)
    edges.push(segment(`c${d.data.key}`, 'gt-edge', Math.min(hx, ...xs), bus, Math.max(hx, ...xs), bus))
    for (const c of kids) {
      edges.push(segment(`k${c.node.person_id}`, edgeClass(c.node), c.x, bus, c.x, c.y))
      c.route = `M${sx} ${sy}V${hy}H${hx}V${bus}H${c.x}V${c.y}`
    }
    if (g.visible) headers.push({ key: d.data.key, parent: g.parent, group: g.key, n: g.n, x: hx, y: hy })
  }
  for (const c of cross) {
    const a = at.get(c.parent)
    const b = at.get(c.child)
    if (!a || !b) continue
    const y0 = a.y + NODE_H
    const bend = Math.max(40, Math.abs(b.y - y0) / 2)
    edges.push({
      key: `x${c.parent}:${c.child}`,
      cls: 'gt-cross',
      d: `M${a.x} ${y0}C${a.x} ${y0 + bend} ${b.x} ${b.y - bend} ${b.x} ${b.y}`,
      box: [Math.min(a.x, b.x), Math.min(y0, b.y) - bend, Math.max(a.x, b.x), Math.max(y0, b.y) + bend],
    })
  }
  const width = (nodes.length ? hi - lo : NODE_W) + 2 * PAD
  const height = Math.max(0, ...nodes.map((n) => n.y)) + NODE_H + PAD
  return { nodes, headers, edges, width, height, at, spouseAt }
}

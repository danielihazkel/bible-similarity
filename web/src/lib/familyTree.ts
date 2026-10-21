// The family tree's layout (DESIGN.md §16.63): the drawn tree indexed once, then laid out by
// d3-hierarchy over the expanded part only. Every expanded person's children hang from a header
// row: one header per mother when the children have more than one (the attached, by a link not
// stated, apart), else an unseen one. So each generation is two levels of the hierarchy and the
// generations line up across the tree.

import { hierarchy, tree } from 'd3-hierarchy'
import type { CrossLink, SkeletonResponse, TreeNode, TreeSpouse } from '../api/types'

export const NODE_W = 104 // a node's width, CSS pixels
export const NODE_H = 46 // ... its height (a name and a line of spouses)
export const COL = 116 // the distance between two sibling nodes
export const ROW = 140 // the distance between generations
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
  x: number // its centre
  y: number // its top
  expanded: boolean
  hidden: number // descendants not drawn (collapsed)
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
}

interface H {
  key: string
  node?: TreeNode
  group?: { key: GroupKey; parent: number; visible: boolean; n: number }
  children?: H[]
}

/** The edge class of the link a child hangs by: a descendant, a link not stated or a son. */
export const edgeClass = (n: TreeNode) => (n.role === 'unstated' ? 'gt-edge unstated' : n.link_kind === 'descendant' ? 'gt-edge desc' : 'gt-edge')

function segment(key: string, cls: string, x0: number, y0: number, x1: number, y1: number): LaidEdge {
  return { key, cls, d: `M${x0} ${y0}L${x1} ${y1}`, box: [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)] }
}

/** The expanded part laid out: node centres and tops, headers, edges (as segments, each with its
 * box, to draw only those in view) and cross-links between nodes both drawn; mirrored for a
 * right-to-left page (the first-born on the right). */
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
        group: { key: g.key, parent: n.person_id, visible: groups.length > 1, n: g.kids.length },
        children: g.kids.map(build),
      })),
    }
  }
  const root = hierarchy<H>({ key: 'top', children: ix.roots.map(build) })
  const laid = tree<H>()
    .nodeSize([COL, 1])
    .separation((a, b) => (a.parent === b.parent ? 1 : 1.25))(root)
  const all = laid.descendants().filter((d) => d.depth > 0)
  let lo = Infinity
  let hi = -Infinity
  for (const d of all) {
    lo = Math.min(lo, d.x)
    hi = Math.max(hi, d.x)
  }
  const X = (x: number) => (rtl ? hi - x : x - lo) + PAD + NODE_W / 2
  // depth 1, 3, 5, ... are people (generation (depth - 1) / 2); 2, 4, ... their headers
  const top = (depth: number) => PAD + ((depth - 1) / 2) * ROW

  const nodes: LaidNode[] = []
  const headers: LaidHeader[] = []
  const edges: LaidEdge[] = []
  const at = new Map<number, LaidNode>()
  for (const d of all) {
    const n = d.data.node
    if (n) {
      const x = X(d.x)
      const ln = { node: n, x, y: top(d.depth), expanded: !!d.children, hidden: d.children ? 0 : (ix.size.get(n.person_id) ?? 0) }
      nodes.push(ln)
      at.set(n.person_id, ln)
      continue
    }
    const g = d.data.group!
    const p = d.parent!
    const px = X(p.x)
    const py = top(p.depth)
    const hx = X(d.x)
    const hy = py + HEADER_Y
    const bus = py + BUS_Y
    // the parent's trunk, out to the header, down to the bus, along it and down to each child
    if (d === p.children![0]) edges.push(segment(`t${g.parent}`, 'gt-edge', px, py + NODE_H, px, hy))
    if (hx !== px) edges.push(segment(`a${d.data.key}`, 'gt-edge', px, hy, hx, hy))
    edges.push(segment(`b${d.data.key}`, 'gt-edge', hx, hy, hx, bus))
    const xs = (d.children ?? []).map((c) => X(c.x))
    edges.push(segment(`c${d.data.key}`, 'gt-edge', Math.min(hx, ...xs), bus, Math.max(hx, ...xs), bus))
    for (const c of d.children ?? []) {
      const cn = c.data.node!
      edges.push(segment(`k${cn.person_id}`, edgeClass(cn), X(c.x), bus, X(c.x), top(c.depth)))
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
  const width = (hi - lo || 0) + NODE_W + 2 * PAD
  const height = Math.max(0, ...nodes.map((n) => n.y)) + NODE_H + PAD
  return { nodes, headers, edges, width, height, at }
}

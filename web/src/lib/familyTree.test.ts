import { describe, expect, it } from 'vitest'
import type { SkeletonResponse, TreeNode } from '../api/types'
import { below, childGroups, indexTree, layoutTree, NODE_W, opening, pathTo, ROW, shownAt } from './familyTree'

const node = (person_id: number, parent: number | null, extra: Partial<TreeNode> = {}): TreeNode => ({
  person_id,
  he: `n${person_id}`,
  sex: 'm',
  kind: 'person',
  placement: parent === null ? 'root' : 'tree',
  parent,
  role: parent === null ? null : 'father',
  link_kind: parent === null ? null : 'son',
  seq: null,
  mother: null,
  book_id: null,
  reviewed: false,
  doubt: false,
  conflict: false,
  spouses: [],
  ...extra,
})

// 1 -> 2, 3 (by 20), 4 (by 21), 5 (attached); 2 -> 6 (a descendant); 9 a second root
const SK: SkeletonResponse = {
  meta: {},
  nodes: [
    node(1, null, { spouses: [20, 21] }),
    node(3, 1, { seq: 1, mother: 20 }),
    node(2, 1, { seq: 0, mother: 20 }),
    node(4, 1, { seq: 2, mother: 21 }),
    node(5, 1, { role: 'unstated', link_kind: 'unstated', placement: 'tribe' }),
    node(6, 2, { link_kind: 'descendant' }),
    node(9, null, { kind: 'virtual', placement: 'virtual', he: '' }),
  ],
  spouses: [
    { person_id: 20, he: 'אשה', sex: 'f', kind: 'person', reviewed: true },
    { person_id: 21, he: 'פילגש', sex: 'f', kind: 'person', reviewed: true },
  ],
  cross: [{ parent: 3, child: 6, role: 'father', kind: 'son' }],
}

describe('indexTree', () => {
  const ix = indexTree(SK)
  it('orders children by TIPNR, the attached last, and counts descendants', () => {
    expect(ix.kids.get(1)?.map((n) => n.person_id)).toEqual([2, 3, 4, 5])
    expect(ix.roots.map((n) => n.person_id)).toEqual([1, 9])
    expect(ix.size.get(1)).toBe(5)
    expect(ix.size.get(2)).toBe(1)
    expect(ix.host.get(21)).toBe(1)
  })
  it('finds a line, the nodes below, the opening generations', () => {
    expect(pathTo(ix, 6)).toEqual([1, 2, 6])
    expect(pathTo(ix, 20)).toEqual([1]) // a spouse: to the one beside her
    expect(shownAt(ix, 21)).toBe(1)
    expect(below(ix, 1).sort()).toEqual([2, 3, 4, 5, 6])
    expect([...opening(ix, 1)]).toEqual([1])
  })
  it('groups children by mother, the attached apart', () => {
    expect(childGroups(ix.kids.get(1)!).map((g) => [g.key, g.kids.map((k) => k.person_id)])).toEqual([
      [20, [2, 3]],
      [21, [4]],
      ['attached', [5]],
    ])
  })
})

describe('layoutTree', () => {
  const ix = indexTree(SK)
  it('lays out only what is open, generations on rows, no two nodes overlapping', () => {
    const closed = layoutTree(ix, new Set(), SK.cross, false)
    expect(closed.nodes.map((n) => n.node.person_id)).toEqual([1, 9])
    expect(closed.at.get(1)?.hidden).toBe(5)

    const l = layoutTree(ix, new Set([1, 2]), SK.cross, false)
    expect(l.nodes.map((n) => n.node.person_id).sort()).toEqual([1, 2, 3, 4, 5, 6, 9])
    const y = (id: number) => l.at.get(id)!.y
    expect(y(2) - y(1)).toBe(ROW)
    expect(y(6) - y(2)).toBe(ROW)
    expect(y(9)).toBe(y(1))
    for (const a of l.nodes)
      for (const b of l.nodes) if (a !== b && a.y === b.y) expect(Math.abs(a.x - b.x)).toBeGreaterThanOrEqual(NODE_W)
    // three mother headers under 1, none under 2 (one group)
    expect(l.headers.map((h) => h.group)).toEqual([20, 21, 'attached'])
    // the edge classes: a descendant, a link not stated; the cross-link drawn
    expect(l.edges.find((e) => e.key === 'k6')?.cls).toBe('gt-edge desc')
    expect(l.edges.find((e) => e.key === 'k5')?.cls).toBe('gt-edge unstated')
    expect(l.edges.filter((e) => e.cls === 'gt-cross')).toHaveLength(1)
    // a right-to-left page mirrors it: the first-born on the right
    const r = layoutTree(ix, new Set([1, 2]), SK.cross, true)
    expect(l.at.get(2)!.x).toBeLessThan(l.at.get(4)!.x)
    expect(r.at.get(2)!.x).toBeGreaterThan(r.at.get(4)!.x)
  })
})

import { describe, expect, it } from 'vitest'
import type { SkeletonResponse, TreeNode } from '../api/types'
import {
  AVATAR,
  below,
  COUPLE,
  childGroups,
  HEADER_Y,
  indexTree,
  type LaidNode,
  layoutTree,
  NODE_H,
  NODE_W,
  opening,
  PAD,
  pathTo,
  ROW,
  shownAt,
} from './familyTree'

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
    // no two avatars overlapping on a row, spouses beside included
    const row = (n: LaidNode) => [n.x, ...n.spouses.map((s) => s.x)]
    for (const a of l.nodes)
      for (const b of l.nodes)
        if (a !== b && a.y === b.y) for (const xa of row(a)) for (const xb of row(b)) expect(Math.abs(xa - xb)).toBeGreaterThanOrEqual(NODE_W)
    // the mothers are beside 1: no header for them, only for the attached; none under 2 (one group)
    expect(l.headers.map((h) => h.group)).toEqual(['attached'])
    // the edge classes: a descendant, a link not stated; the cross-link drawn
    expect(l.edges.find((e) => e.key === 'k6')?.cls).toBe('gt-edge desc')
    expect(l.edges.find((e) => e.key === 'k5')?.cls).toBe('gt-edge unstated')
    expect(l.edges.filter((e) => e.cls === 'gt-cross')).toHaveLength(1)
    // a right-to-left page mirrors it: the first-born on the right
    const r = layoutTree(ix, new Set([1, 2]), SK.cross, true)
    expect(l.at.get(2)!.x).toBeLessThan(l.at.get(4)!.x)
    expect(r.at.get(2)!.x).toBeGreaterThan(r.at.get(4)!.x)
  })

  it('draws spouses beside: the first on the first-born’s side, the second on the other; mirrored right to left', () => {
    const l = layoutTree(ix, new Set([1]), [], false)
    const one = l.at.get(1)!
    expect(one.spouses).toEqual([
      { id: 20, x: one.x - COUPLE },
      { id: 21, x: one.x + COUPLE },
    ])
    expect(l.spouseAt.get(20)).toEqual({ x: one.x - COUPLE, y: one.y, host: 1 })
    expect(l.edges.find((e) => e.key === 's1:20')?.cls).toBe('gt-couple')
    const r = layoutTree(ix, new Set([1]), [], true)
    expect(r.spouseAt.get(20)!.x).toBe(r.at.get(1)!.x + COUPLE)
    // one spouse: the unit centred between the two
    const sk2: SkeletonResponse = { ...SK, nodes: [node(1, null, { spouses: [20] }), node(2, 1, { mother: 20 })], cross: [] }
    const l2 = layoutTree(indexTree(sk2), new Set([1]), [], false)
    const p = l2.at.get(1)!
    expect(l2.at.get(2)!.x).toBe(p.x - COUPLE / 2)
    expect(l2.width).toBe(COUPLE + NODE_W + 2 * PAD)
  })

  it('hangs a mother’s children from the line between her and the father, and routes each line', () => {
    const l = layoutTree(ix, new Set([1, 2]), [], false)
    const one = l.at.get(1)!
    const mid = one.x - COUPLE / 2 // between 1 and his first wife, 20, on the first-born's side
    const midY = one.y + AVATAR / 2
    expect(l.edges.find((e) => e.key === 't1:20')?.d).toBe(`M${mid} ${midY}L${mid} ${one.y + HEADER_Y}`)
    expect(l.edges.find((e) => e.key === 't1:21')?.d).toBe(`M${one.x + COUPLE / 2} ${midY}L${one.x + COUPLE / 2} ${one.y + HEADER_Y}`)
    // the attached hang from under him
    expect(l.edges.find((e) => e.key === 't1:p')?.d).toBe(`M${one.x} ${one.y + NODE_H}L${one.x} ${one.y + HEADER_Y}`)
    const two = l.at.get(2)!
    expect(two.route?.startsWith(`M${mid} ${midY}V`)).toBe(true)
    expect(two.route?.endsWith(`H${two.x}V${two.y}`)).toBe(true)
    expect(l.at.get(6)!.route?.startsWith(`M${two.x} ${two.y + NODE_H}V`)).toBe(true)
    expect(one.route).toBeUndefined()
  })

  it('keeps a header for a mother not beside (a third wife)', () => {
    const sk3: SkeletonResponse = {
      ...SK,
      nodes: [node(1, null, { spouses: [20, 21, 22] }), node(2, 1, { mother: 20 }), node(3, 1, { mother: 22 })],
      spouses: [...SK.spouses, { person_id: 22, he: 'שלישית', sex: 'f', kind: 'person', reviewed: true }],
      cross: [],
    }
    const l = layoutTree(indexTree(sk3), new Set([1]), [], false)
    expect(l.at.get(1)!.spouses.map((s) => s.id)).toEqual([20, 21])
    expect(l.headers.map((h) => h.group)).toEqual([22])
  })
})

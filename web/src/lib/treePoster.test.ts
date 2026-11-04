// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import type { SkeletonResponse, TreeNode } from '../api/types'
import { indexTree } from './familyTree'
import { MIN_W, nameLines, POSTER_COLOURS, type PosterText, posterLayout, posterSvg } from './treePoster'

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
  reviewed: true,
  doubt: false,
  conflict: false,
  spouses: [],
  ...extra,
})

// 1 (wives 20, 21) -> 2, 3 (by 20), 4 (by 21), 5 (attached); 2 -> 6 (a descendant) -> 7; 9 a second root
const SK: SkeletonResponse = {
  meta: {},
  nodes: [
    node(1, null, { he: 'אברהם', spouses: [20, 21] }),
    node(3, 1, { seq: 1, mother: 20, conflict: true }),
    node(2, 1, { seq: 0, mother: 20 }),
    node(4, 1, { seq: 2, mother: 21, sex: 'f', reviewed: false }),
    node(5, 1, { role: 'unstated', link_kind: 'unstated', placement: 'tribe', he: 'a <b> & "c"' }),
    node(6, 2, { link_kind: 'descendant' }),
    node(7, 6),
    node(9, null, { kind: 'virtual', placement: 'virtual', he: '' }),
  ],
  spouses: [
    { person_id: 20, he: 'שרה', sex: 'f', kind: 'person', reviewed: true },
    { person_id: 21, he: 'הגר', sex: 'f', kind: 'person', reviewed: true },
  ],
  cross: [{ parent: 3, child: 6, role: 'father', kind: 'son' }],
}
const ix = indexTree(SK)
const name = (id: number) => {
  const p = ix.byId.get(id) ?? ix.spouse.get(id)
  return { text: p?.he ?? '', he: /[֐-׿]/.test(p?.he ?? '') }
}
const TEXT: PosterText = {
  title: 'The family tree from אברהם',
  subtitle: '8 people in 3 generations',
  site: 'Tanakh Similarity',
  header: (g, n) => (typeof g === 'number' ? `by ${name(g).text}` : g === 'none' ? 'mother not named' : `not stated (${n})`),
  hidden: (n) => `+${n} below`,
  moreSpouses: (n) => `+${n} spouses`,
  keys: { child: 'Parent and child', couple: 'Husband and wife', desc: 'A descendant', unstated: 'Not stated', cross: 'Another parent', unreviewed: 'Not checked', conflict: 'Two parents' },
}
const parse = (svg: string) => new DOMParser().parseFromString(svg, 'image/svg+xml')

describe('posterLayout', () => {
  it('lays out the people below one as they are opened, and counts them', () => {
    const p = posterLayout(ix, 1, new Set([1, 2]), SK.cross, false)!
    expect(p.root).toBe(1)
    // 1 and two wives; 2, 3, 4, 5; 6 (closed, so 7 not drawn)
    expect(p.people).toBe(8)
    expect(p.generations).toBe(3)
    expect(p.layout.nodes.map((n) => n.node.person_id).sort()).toEqual([1, 2, 3, 4, 5, 6])
    expect(p.layout.nodes.find((n) => n.node.person_id === 6)!.hidden).toBe(1)
    // the second root is not on this poster
    expect(p.layout.at.has(9)).toBe(false)
  })

  it('starts lower down, without the lines to those not drawn, and from the husband of a wife', () => {
    const p = posterLayout(ix, 2, new Set([1, 2, 6]), SK.cross, false)!
    expect(p.layout.nodes.map((n) => n.node.person_id)).toEqual([2, 6, 7])
    expect(p.generations).toBe(3)
    expect(p.layout.edges.some((e) => e.cls === 'gt-cross')).toBe(false)
    expect(posterLayout(ix, 20, new Set([1]), SK.cross, false)!.root).toBe(1)
    expect(posterLayout(ix, 99, new Set(), SK.cross, false)).toBeUndefined()
  })
})

describe('nameLines', () => {
  it('wraps a name in two lines at most', () => {
    expect(nameLines('אברהם')).toEqual(['אברהם'])
    expect(nameLines('the daughter of Lot', 15)).toEqual(['the daughter of', 'Lot'])
    expect(nameLines('one two three four five six seven', 9)).toEqual(['one two', 'three fo…'])
  })
})

describe('posterSvg', () => {
  const p = posterLayout(ix, 1, new Set([1, 2]), SK.cross, false)!
  const svg = posterSvg(p.layout, ix, name, TEXT, { rtl: false })
  const doc = parse(svg)
  const texts = () => [...doc.querySelectorAll('text')]

  it('writes one well-formed SVG file with its title, size and legend', () => {
    expect(doc.getElementsByTagName('parsererror')).toHaveLength(0)
    const root = doc.documentElement
    expect(root.getAttribute('xmlns')).toBe('http://www.w3.org/2000/svg')
    expect(Number(root.getAttribute('width'))).toBeGreaterThanOrEqual(MIN_W)
    expect(root.getAttribute('viewBox')).toBe(`0 0 ${root.getAttribute('width')} ${root.getAttribute('height')}`)
    expect(doc.querySelector('title')!.textContent).toBe('The family tree from אברהם')
    const all = texts().map((t) => t.textContent)
    for (const k of Object.values(TEXT.keys)) expect(all).toContain(k)
    expect(all).toContain('Tanakh Similarity')
  })

  it('draws everyone opened, each name under an avatar, Hebrew right to left', () => {
    // one avatar per person drawn
    expect(doc.querySelectorAll('use')).toHaveLength(8)
    const avr = texts().find((t) => t.textContent === 'אברהם')!
    expect(avr.getAttribute('direction')).toBe('rtl')
    expect(texts().some((t) => t.textContent === 'שרה')).toBe(true)
    // a name's markup escaped, its text kept
    expect(svg).toContain('a &lt;b&gt; &amp; &quot;c&quot;')
    expect(texts().some((t) => t.textContent === 'a <b> & "c"')).toBe(true)
    // 6 is closed: what is not drawn is said
    expect(texts().some((t) => t.textContent === '+1 below')).toBe(true)
    // both wives are drawn beside him, so no header by mother; the attached one has its header
    expect(texts().some((t) => t.textContent === 'not stated (1)')).toBe(true)
  })

  it('marks the figures: a woman, one not checked, a conflict, a descendant line', () => {
    const uses = [...doc.querySelectorAll('use')].map((u) => u.getAttribute('href'))
    expect(uses.filter((h) => h === '#av-woman')).toHaveLength(3)
    expect(doc.querySelector('#av-man')).not.toBeNull()
    expect(svg).toContain(`stroke="${POSTER_COLOURS.conflict}" stroke-width="2.5"`)
    expect(svg).toContain('stroke-dasharray="3 2.5"')
    expect(svg).toContain(`stroke="${POSTER_COLOURS.desc}" stroke-width="2.2" stroke-dasharray="6 4"`)
  })

  it('takes the stylesheet’s colours, when written as #rrggbb', () => {
    const own = posterSvg(p.layout, ix, name, TEXT, { rtl: false, colours: { line: '#123456', text: 'rgb(1, 2, 3)' } })
    expect(own).toContain('stroke="#123456" stroke-width="1.6"')
    expect(own).toContain(`fill="${POSTER_COLOURS.text}"`)
  })

  it('sets a right-to-left poster from the right', () => {
    const rl = parse(posterSvg(p.layout, ix, name, TEXT, { rtl: true }))
    const title = rl.querySelectorAll('text')[0]
    const w = Number(rl.documentElement.getAttribute('width'))
    expect(title.getAttribute('direction')).toBe('rtl')
    expect(Number(title.getAttribute('x'))).toBeGreaterThan(w / 2)
  })
})

// The family tree as a poster (DESIGN.md §11.1, print and export): the people below one person,
// as they are opened in the tree, laid out as on screen (`layoutTree`) and written as one SVG file
// to print large: a title, the avatars with names under them, the lines between them, a legend.

import type { CrossLink } from '../api/types'
import { AVATAR_PARTS, type AvatarShape, avatarShape } from './avatarShapes'
import { AVATAR, type FamilyIndex, HEADER_H, layoutTree, NODE_W, ROW, PAD, SPOUSES_SHOWN, type TreeLayout } from './familyTree'
import { xmlEscape as esc } from './svgExport'

export const TITLE_H = 96 // the title block above the tree
export const LEGEND_ROW = 26 // a legend row's height, under the tree
export const MIN_W = 720 // the narrowest poster (a person with few below)
const NAME_FONT = 13
const NAME_CHARS = 15 // a name line's length before it wraps (NODE_W at NAME_FONT)
const SMALL_FONT = 10.5
const KEY_CHAR = 6.4 // a legend letter's width at 12px, for laying the legend out

/** The poster's colours: the light theme's tokens (`lightToken`), these where none are read. */
export const POSTER_COLOURS = {
  text: '#2a2218',
  muted: '#7a6c58',
  border: '#e2d7c3',
  paper: '#ffffff',
  shelf: '#f3ecdf', // a book's avatar (the "unattached")
  avatar: '#efe5d3',
  ink: '#3d3224',
  ring: '#ddcfb6',
  line: '#a8957a',
  couple: '#a0703a',
  desc: '#7b4fb0',
  unstated: '#8a8172',
  cross: '#3f7cac',
  conflict: '#b7791f',
}
export type PosterColours = typeof POSTER_COLOURS
/** The stylesheet's token behind each colour (the paper stays white). */
export const POSTER_TOKENS: Partial<Record<keyof PosterColours, string>> = {
  text: '--text',
  muted: '--muted',
  border: '--border',
  shelf: '--surface-2',
  avatar: '--gt-avatar',
  ink: '--gt-avatar-ink',
  ring: '--gt-ring',
  line: '--gt-line',
  couple: '--gt-couple',
  desc: '--gt-desc',
  unstated: '--gt-unstated',
  cross: '--gt-cross',
  conflict: '--gt-conflict',
}

export const FONTS = {
  he: "'Ezra SIL', 'SBL Hebrew', 'Noto Serif Hebrew', 'Times New Roman', serif",
  ui: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
}

export interface Named {
  text: string
  he: boolean
}

export interface PosterText {
  title: string
  subtitle: string
  site: string
  /** A header's label: the mother's name, "mother not named", "not stated (n)". */
  header: (group: number | 'none' | 'attached', n: number) => string
  hidden: (n: number) => string // "+12 below", under a person not opened
  moreSpouses: (n: number) => string
  keys: { child: string; couple: string; desc: string; unstated: string; cross: string; unreviewed: string; conflict: string }
}

/** The part of the tree a poster draws: the person (or the one they are drawn beside) and those
 * below them who are opened, laid out alone; with the count of people and generations. */
export function posterLayout(ix: FamilyIndex, id: number, expanded: Set<number>, cross: CrossLink[], rtl: boolean) {
  const at = ix.byId.has(id) ? id : ix.host.get(id)
  const root = at === undefined ? undefined : ix.byId.get(at)
  if (!root) return undefined
  const layout = layoutTree({ ...ix, roots: [root] }, expanded, cross, rtl)
  const people = layout.nodes.reduce((t, n) => t + 1 + n.spouses.length, 0)
  const generations = Math.round((Math.max(...layout.nodes.map((n) => n.y)) - PAD) / ROW) + 1
  return { root: root.person_id, layout, people, generations }
}

/** A name in lines of about NAME_CHARS, at most two (the second cut short with "…"). */
export function nameLines(text: string, chars = NAME_CHARS): string[] {
  const words = text.split(/\s+/).filter(Boolean)
  const lines: string[] = []
  for (const w of words) {
    const last = lines.length - 1
    if (last >= 0 && (lines[last] + ' ' + w).length <= chars) lines[last] += ' ' + w
    else lines.push(w)
  }
  if (lines.length <= 2) return lines
  const second = lines.slice(1).join(' ')
  return [lines[0], second.length > chars ? `${second.slice(0, chars - 1).trimEnd()}…` : second]
}

const fmt = (n: number) => String(Math.round(n * 10) / 10)

const EDGE_LOOK = (c: PosterColours): Record<string, string> => ({
  'gt-edge': `stroke="${c.line}" stroke-width="1.6"`,
  'gt-edge desc': `stroke="${c.desc}" stroke-width="2.2" stroke-dasharray="6 4"`,
  'gt-edge unstated': `stroke="${c.unstated}" stroke-width="2.2" stroke-dasharray="0.5 4.5" stroke-linecap="round"`,
  'gt-couple': `stroke="${c.couple}" stroke-width="2" stroke-dasharray="4 4"`,
  'gt-cross': `stroke="${c.cross}" stroke-width="1.3" stroke-dasharray="8 3 2 3"`,
})

/** The avatars, each once, used by every person (`<use>`): the figure clipped to its circle (a
 * book's to a rounded square); a person of unknown sex drawn fainter. */
function symbols(c: PosterColours): string {
  const faint = mix(c.ink, c.avatar, 0.55)
  const body = (shape: AvatarShape, ink: string) =>
    AVATAR_PARTS[shape]
      .map((p) => {
        const front = p.front ? ` stroke="${c.avatar}" stroke-width="1.6"` : ''
        return 'c' in p ? `<circle cx="${p.c[0]}" cy="${p.c[1]}" r="${p.c[2]}" fill="${ink}"${front}/>` : `<path d="${p.d}" fill="${ink}"${front}/>`
      })
      .join('')
  const round = (id: string, shape: AvatarShape, ink: string) =>
    `<symbol id="${id}" viewBox="0 0 44 44"><circle cx="22" cy="22" r="22" fill="${c.avatar}"/><g clip-path="url(#av-clip)">${body(shape, ink)}</g></symbol>`
  return [
    '<clipPath id="av-clip"><circle cx="22" cy="22" r="22"/></clipPath>',
    round('av-man', 'man', c.ink),
    round('av-woman', 'woman', c.ink),
    round('av-x', 'man', faint),
    round('av-group', 'group', c.ink),
    `<symbol id="av-book" viewBox="0 0 44 44"><rect x="0.5" y="0.5" width="43" height="43" rx="12" fill="${c.shelf}" stroke="${c.border}"/>${body('book', c.ink)}</symbol>`,
  ].join('')
}

/** a × w + b × (1 − w), for two #rrggbb colours. */
function mix(a: string, b: string, w: number): string {
  const ch = (h: string, i: number) => parseInt(h.slice(1 + 2 * i, 3 + 2 * i), 16)
  if (!/^#[0-9a-f]{6}$/i.test(a) || !/^#[0-9a-f]{6}$/i.test(b)) return a
  return `#${[0, 1, 2].map((i) => Math.round(ch(a, i) * w + ch(b, i) * (1 - w)).toString(16).padStart(2, '0')).join('')}`
}

interface Figure {
  x: number
  y: number
  shape: string // the symbol's id
  name: Named
  reviewed: boolean
  conflict: boolean
  anon: boolean
  notes: string[] // lines under the name: "+12 below", "+1 spouse"
}

function figure(f: Figure, c: PosterColours, rtl: boolean): string {
  const cx = f.x
  const cy = f.y + AVATAR / 2
  const ring = f.conflict
    ? `<circle cx="${fmt(cx)}" cy="${fmt(cy)}" r="23.25" fill="none" stroke="${c.conflict}" stroke-width="2.5"/>`
    : f.reviewed
      ? `<circle cx="${fmt(cx)}" cy="${fmt(cy)}" r="22.75" fill="none" stroke="${c.ring}" stroke-width="1.5"/>`
      : `<circle cx="${fmt(cx)}" cy="${fmt(cy)}" r="23.75" fill="none" stroke="${c.muted}" stroke-width="1.5" stroke-dasharray="3 2.5"/>`
  const use = `<use xlink:href="#${f.shape}" href="#${f.shape}" x="${fmt(f.x - AVATAR / 2)}" y="${fmt(f.y)}" width="${AVATAR}" height="${AVATAR}"${f.anon ? ' opacity="0.6"' : ''}/>`
  const lines = nameLines(f.name.text)
  // a right-to-left line (a Hebrew name, any text of the Hebrew interface) is set so: its parts in order
  const dir = rtl || f.name.he ? ' direction="rtl"' : ''
  const font = f.name.he ? `font-family="${esc(FONTS.he)}" font-size="${NAME_FONT + 2}"${dir}` : `font-family="${esc(FONTS.ui)}" font-size="${NAME_FONT}"${dir}`
  const name = lines
    .map((l, i) => `<text x="${fmt(cx)}" y="${fmt(f.y + AVATAR + 16 + i * 15)}" text-anchor="middle" fill="${c.text}" ${font}>${esc(l)}</text>`)
    .join('')
  const notes = f.notes
    .map(
      (l, i) =>
        `<text x="${fmt(cx)}" y="${fmt(f.y + AVATAR + 16 + lines.length * 15 + i * 13)}" text-anchor="middle" fill="${c.muted}" font-family="${esc(FONTS.ui)}" font-size="${SMALL_FONT}"${rtl ? ' direction="rtl"' : ''}>${esc(l)}</text>`,
    )
    .join('')
  return `<g>${ring}${use}${name}${notes}</g>`
}

/** The legend under the tree: a line or a ring, then its meaning; rows wrap at the poster's width. */
function legend(text: PosterText, c: PosterColours, width: number, rtl: boolean): { svg: string; height: number } {
  const look = EDGE_LOOK(c)
  const items: { mark: (x: number, y: number) => string; label: string }[] = [
    ...(
      [
        ['gt-edge', text.keys.child],
        ['gt-couple', text.keys.couple],
        ['gt-edge desc', text.keys.desc],
        ['gt-edge unstated', text.keys.unstated],
        ['gt-cross', text.keys.cross],
      ] as const
    ).map(([cls, label]) => ({ mark: (x: number, y: number) => `<path d="M${fmt(x)} ${fmt(y)}h30" fill="none" ${look[cls]}/>`, label })),
    { mark: (x, y) => `<circle cx="${fmt(x + 15)}" cy="${fmt(y)}" r="8" fill="${c.avatar}" stroke="${c.muted}" stroke-width="1.5" stroke-dasharray="3 2.5"/>`, label: text.keys.unreviewed },
    { mark: (x, y) => `<circle cx="${fmt(x + 15)}" cy="${fmt(y)}" r="8" fill="${c.avatar}" stroke="${c.conflict}" stroke-width="2.5"/>`, label: text.keys.conflict },
  ]
  const out: string[] = []
  let x = PAD
  let row = 0
  for (const it of items) {
    const w = 30 + 8 + it.label.length * KEY_CHAR + 28
    if (x > PAD && x + w > width - PAD) {
      x = PAD
      row++
    }
    const y = row * LEGEND_ROW + LEGEND_ROW / 2
    // laid out from the right on a right-to-left poster; a right-to-left text starts at its right
    const mx = rtl ? width - x - 30 : x
    const tx = rtl ? mx - 8 : mx + 38
    out.push(
      it.mark(mx, y),
      `<text x="${fmt(tx)}" y="${fmt(y + 4)}" text-anchor="start" fill="${c.text}" font-family="${esc(FONTS.ui)}" font-size="12"${rtl ? ' direction="rtl"' : ''}>${esc(it.label)}</text>`,
    )
    x += w
  }
  return { svg: out.join(''), height: (row + 1) * LEGEND_ROW }
}

/** The poster: the laid-out tree under a title, with its legend, as one SVG file. */
export function posterSvg(
  layout: TreeLayout,
  ix: FamilyIndex,
  name: (id: number) => Named,
  text: PosterText,
  opts: { rtl: boolean; colours?: Partial<PosterColours> },
): string {
  // only colours written as #rrggbb (the poster mixes them); the rest as defined here
  const c: PosterColours = { ...POSTER_COLOURS, ...Object.fromEntries(Object.entries(opts.colours ?? {}).filter(([, v]) => /^#[0-9a-f]{6}$/i.test(v ?? ''))) }
  const width = Math.max(MIN_W, Math.ceil(layout.width))
  const dx = (width - layout.width) / 2
  const key = legend(text, c, width, opts.rtl)
  const height = Math.ceil(TITLE_H + layout.height + 16 + key.height + PAD)
  const look = EDGE_LOOK(c)

  // the lines, one group per kind
  const byCls = new Map<string, string[]>()
  for (const e of layout.edges) byCls.set(e.cls, [...(byCls.get(e.cls) ?? []), e.d])
  const edges = [...byCls.entries()].map(([cls, ds]) => `<g fill="none" ${look[cls] ?? look['gt-edge']}>${ds.map((d) => `<path d="${d}"/>`).join('')}</g>`).join('')

  const headers = layout.headers
    .map((h) => {
      const label = text.header(h.group, h.n)
      const short = label.length > 17 ? `${label.slice(0, 16)}…` : label
      return (
        `<rect x="${fmt(h.x - NODE_W / 2)}" y="${fmt(h.y - HEADER_H / 2)}" width="${NODE_W}" height="${HEADER_H}" rx="11" fill="${c.paper}" stroke="${c.border}"${h.group === 'attached' ? ' stroke-dasharray="1.5 2"' : ''}/>` +
        `<text x="${fmt(h.x)}" y="${fmt(h.y + 4)}" text-anchor="middle" fill="${c.muted}" font-family="${esc(FONTS.ui)}" font-size="11"${opts.rtl ? ' direction="rtl"' : ''}>${esc(short)}</text>`
      )
    })
    .join('')

  const figures: string[] = []
  for (const ln of layout.nodes) {
    const n = ln.node
    const notes: string[] = []
    if (ln.hidden > 0) notes.push(text.hidden(ln.hidden))
    if (n.spouses.length > SPOUSES_SHOWN) notes.push(text.moreSpouses(n.spouses.length - SPOUSES_SHOWN))
    figures.push(
      figure(
        {
          x: ln.x,
          y: ln.y,
          shape: n.kind === 'virtual' ? 'av-book' : n.kind === 'group' ? 'av-group' : n.sex === null ? 'av-x' : `av-${avatarShape(n.sex, n.kind)}`,
          name: name(n.person_id),
          reviewed: n.kind === 'virtual' || n.reviewed,
          conflict: n.conflict,
          anon: n.kind === 'anon',
          notes,
        },
        c,
        opts.rtl,
      ),
    )
    for (const s of ln.spouses) {
      const p = ix.spouse.get(s.id)
      figures.push(
        figure(
          {
            x: s.x,
            y: ln.y,
            shape: p?.kind === 'group' ? 'av-group' : p?.sex === null || p?.sex === undefined ? 'av-x' : `av-${avatarShape(p.sex, p.kind)}`,
            name: name(s.id),
            reviewed: !!p?.reviewed,
            conflict: false,
            anon: p?.kind === 'anon',
            notes: [],
          },
          c,
          opts.rtl,
        ),
      )
    }
  }

  // with direction="rtl" a text's start is its right end: the title on the right, the site on the left
  const tx = opts.rtl ? width - PAD : PAD
  const dir = opts.rtl ? ' direction="rtl"' : ''
  const head =
    `<text x="${tx}" y="${PAD + 26}" text-anchor="start" fill="${c.text}" font-family="${esc(FONTS.he)}" font-size="28" font-weight="600"${dir}>${esc(text.title)}</text>` +
    `<text x="${tx}" y="${PAD + 50}" text-anchor="start" fill="${c.muted}" font-family="${esc(FONTS.ui)}" font-size="13"${dir}>${esc(text.subtitle)}</text>` +
    `<text x="${opts.rtl ? PAD : width - PAD}" y="${PAD + 26}" text-anchor="end" fill="${c.muted}" font-family="${esc(FONTS.ui)}" font-size="12"${dir}>${esc(text.site)}</text>`

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    `<title>${esc(text.title)}</title>`,
    `<defs>${symbols(c)}</defs>`,
    `<rect width="${width}" height="${height}" fill="${c.paper}"/>`,
    head,
    `<g transform="translate(${fmt(dx)} ${TITLE_H})">${edges}${headers}${figures.join('')}</g>`,
    `<g transform="translate(0 ${fmt(TITLE_H + layout.height + 16)})">${key.svg}</g>`,
    '</svg>',
    '',
  ].join('\n')
}

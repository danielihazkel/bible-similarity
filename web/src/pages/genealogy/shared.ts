// The family tree page's shared pieces: view constants, how a person is named.
import type { Messages } from '../../i18n'
import type { FamilyIndex } from '../../lib/familyTree'

export const OPEN_GENERATIONS = 3 // the tree opens with Adam's first generations expanded
export const K_MIN = 0.02 // zoom limits (at the least, the whole tree opened)
export const K_MAX = 3
export const K_SMALL = 0.45 // below this zoom, names only: no lines under them, no open / close buttons
export const K_DOTS = 0.22 // ... and below this, each person a dot
export const K_DOT = 0.9 // the zoom a click on a dot goes to
export const DOT_MIN = 2.5 // CSS pixels a dot keeps on screen however far out
export const ZOOM = 1.4 // a step of the + / − buttons and keys
export const KEY_STEP = 80 // CSS pixels an arrow key moves the tree
export const MARGIN = 160 // CSS pixels beyond the view still drawn
export const FIT_PAD = 24 // CSS pixels around the tree fitted into view
export const MEMBERS_SHOWN = 40 // people attached to a node listed before "show all"

export type T = Messages['gt']
export type Named = { text: string; he: boolean }
export type Namer = (id: number) => Named

/** A person's name as the tree writes it: the Hebrew name; for the unnamed, what they are to the
 * one they are drawn under or beside ("בת לוט"); for the "unattached" groups, the book. */
export function namer(ix: FamilyIndex, t: T, books: Map<number, string>): Namer {
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


/** Overview → Family tree (§16.63, D103): everyone the text names, from Adam down, collapsible at
 * any node, on most of the screen; a person (`?p=`) opens the line down to them, lights it, and
 * opens a card over the tree with their family and the verses that state each link. */
